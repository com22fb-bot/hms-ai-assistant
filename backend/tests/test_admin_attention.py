import os
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault("OAUTH_ENCRYPTION_KEY", "test-oauth-encryption-key-32chars!!")

from fastapi import HTTPException

from app.api import admin_attention as mod


class _Q:
    def __init__(self, client, table):
        self.c, self.t, self.f = client, table, {}

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self.f[col] = val
        return self

    def in_(self, col, vals):
        self.f[col] = tuple(vals)
        return self

    def gte(self, col, val):
        self.f[col + ">="] = val
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a):
        return self

    def execute(self):
        if self.t in self.c.fail:
            raise RuntimeError("boom")
        key = (self.t, tuple(sorted((k, v) for k, v in self.f.items() if not k.endswith(">="))))
        return SimpleNamespace(count=self.c.counts.get(key, 0), data=self.c.rows.get(self.t, []))


class FakeClient:
    def __init__(self, counts=None, rows=None, fail=()):
        self.counts, self.rows, self.fail = counts or {}, rows or {}, set(fail)

    def table(self, name):
        return _Q(self, name)


NOW = datetime(2026, 10, 23, 19, 0, tzinfo=timezone.utc)


class CommercialMetricsTests(unittest.TestCase):
    def test_no_fake_zeros_for_uninstrumented_metrics(self):
        m = mod.commercial_metrics(FakeClient())
        for key in ("trials_active", "subscriptions_active", "mrr_cents", "arr_cents",
                    "payments_confirmed", "feedback_open", "signed_up_no_product_use_24h"):
            self.assertIsNone(m[key]["value"], key)
            self.assertEqual(m[key]["status"], mod.PENDING, key)

    def test_real_counts_and_real_zero(self):
        c = FakeClient(counts={("profiles", ()): 5,
                               ("communication_accounts", (("status", "active"),)): 3})
        m = mod.commercial_metrics(c)
        self.assertEqual(m["users"], {"value": 5, "status": "real", "source": "supabase.profiles", "note": ""})
        self.assertEqual(m["mailboxes_active"]["value"], 3)
        self.assertEqual(m["mailboxes_needs_reauth"]["value"], 0)  # cero real
        self.assertEqual(m["mailboxes_needs_reauth"]["status"], mod.REAL)

    def test_query_error_is_not_zero(self):
        m = mod.commercial_metrics(FakeClient(fail={"profiles"}))
        self.assertIsNone(m["users"]["value"])
        self.assertEqual(m["users"]["status"], mod.QUERY_ERROR)


class AttentionTests(unittest.TestCase):
    def test_healthy_system_only_owner_decisions(self):
        items = mod.attention_items(FakeClient(), now=NOW)
        self.assertEqual({i["category"] for i in items}, {"decision_propietario"})

    def test_items_sorted_by_severity(self):
        c = FakeClient(
            counts={("communication_accounts", (("status", "needs_reauth"),)): 2,
                    ("contact_messages", (("status", "nuevo"),)): 4,
                    ("gmail_sync_jobs", (("status", "failed"),)): 1},
            rows={"system_incidents": [{"id": "x", "incident_code": "INC-1", "component": "gmail",
                                        "severity": "critical", "summary": "caída", "status": "open",
                                        "occurred_at": "2026-10-23T18:00:00Z"}]},
        )
        items = mod.attention_items(c, now=NOW)
        sev = [i["severity"] for i in items]
        self.assertEqual(sev[0], "critical")
        self.assertEqual(sev, sorted(sev, key=lambda s: mod.SEVERITY_RANK[s]))
        ids = {i["id"] for i in items}
        self.assertTrue({"mailboxes:needs_reauth", "sync:failed_24h", "contact:nuevo"} <= ids)

    def test_query_failure_surfaces_as_item_not_silence(self):
        items = mod.attention_items(FakeClient(fail={"system_incidents", "gmail_sync_jobs"}), now=NOW)
        ids = {i["id"] for i in items}
        self.assertIn("query-error:system_incidents", ids)
        self.assertIn("query-error:gmail_sync_jobs", ids)

    def test_no_sensitive_fields(self):
        c = FakeClient(rows={"system_incidents": [{"id": "x", "component": "c", "severity": "low",
                                                   "summary": "s", "status": "open",
                                                   "technical_detail": "SECRET"}]})
        self.assertNotIn("SECRET", repr(mod.attention_items(c, now=NOW)))

    def test_endpoint_requires_admin(self):
        ctx = SimpleNamespace(user=SimpleNamespace(id="u", email="otro@x.com"))
        with patch.dict(os.environ, {"ADMIN_EMAILS": "hmcelinfo@gmail.com"}), \
             patch("app.api.admin_ops.require_request_context", return_value=ctx):
            with self.assertRaises(HTTPException) as e:
                mod.admin_attention()
        self.assertEqual(e.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
