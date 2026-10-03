"""Insights are attached on read, from stored rows, without any write."""

from __future__ import annotations

import os
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(__file__))

from mail_fixtures import FIXTURES  # noqa: E402

from app.schemas.cases import CaseListItem  # noqa: E402
from app.services.insight_attach import attach_case_insights, attach_thread_insights  # noqa: E402


class FakeQuery:
    def __init__(self, client: "FakeClient", table: str) -> None:
        self.client, self.table, self.filters = client, table, []

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, key, value):
        self.filters.append((key, {value}))
        return self

    def in_(self, key, values):
        self.filters.append((key, set(values)))
        return self

    def execute(self):
        rows = [r for r in self.client.tables[self.table] if all(str(r.get(k)) in {str(v) for v in vals} for k, vals in self.filters)]
        return SimpleNamespace(data=rows)

    def __getattr__(self, name):  # insert/update/delete/upsert must never be used
        if name in {"insert", "update", "delete", "upsert"}:
            self.client.writes.append(name)
        raise AttributeError(name)


class FakeClient:
    def __init__(self, tables):
        self.tables, self.writes = tables, []

    def table(self, name):
        return FakeQuery(self, name)


def _message(fixture, index):
    return {
        "id": f"m{index}", "account_id": "acc", "subject": fixture["subject"], "sender": fixture["sender"],
        "body_text": fixture["body_text"], "body_html": fixture["body_html"], "snippet": fixture["subject"],
        "triage_category": "review", "direction": "inbound",
    }


class AttachTests(unittest.TestCase):
    def setUp(self) -> None:
        self.messages = [_message(fixture, i) for i, fixture in enumerate(FIXTURES[:5])]
        self.client = FakeClient({
            "communication_messages": self.messages + [{**_message(FIXTURES[5], 99), "account_id": "other"}],
            "case_messages": [
                {"case_id": "c1", "message_id": "m3", "is_primary": True, "linked_at": "2026-10-01"},
                {"case_id": "c1", "message_id": "m4", "is_primary": False, "linked_at": "2026-10-02"},
            ],
        })

    def test_threads_get_insight_and_clean_summary(self) -> None:
        threads = [{"latest_message_id": "m0", "summary": "Rechazo por saldo insuficiente"}, {"latest_message_id": "m99", "summary": "x"}]
        out = attach_thread_insights(self.client, "acc", threads)
        self.assertEqual(out[0]["insight"]["kind"], "payment_declined")
        self.assertIn("Monto de rechazo", out[0]["summary"])
        # Another account's message is never read into this payload.
        self.assertNotIn("insight", out[1])
        self.assertEqual(self.client.writes, [])

    def test_cases_use_the_primary_message(self) -> None:
        cases = attach_case_insights(self.client, "acc", [{"id": "c1"}, {"id": "c2"}])
        self.assertEqual(cases[0]["insight"]["kind"], "debt_overdue")
        self.assertNotIn("insight", cases[1])
        self.assertEqual(self.client.writes, [])

    def test_failures_return_the_payload_unchanged(self) -> None:
        broken = SimpleNamespace(table=lambda _name: (_ for _ in ()).throw(RuntimeError("db down")))
        rows = [{"latest_message_id": "m0", "summary": "s"}]
        self.assertEqual(attach_thread_insights(broken, "acc", rows), rows)
        self.assertEqual(attach_case_insights(broken, "acc", [{"id": "c1"}]), [{"id": "c1"}])

    def test_case_schema_accepts_insight(self) -> None:
        item = CaseListItem.model_validate({
            "id": "00000000-0000-0000-0000-000000000001", "title": "t", "case_type": "general", "status": "new",
            "priority": "normal", "risk_score": 10, "confidence": 0.7, "waiting_on": "internal",
            "opened_at": "2026-10-01T00:00:00Z", "last_activity_at": "2026-10-01T00:00:00Z",
            "source_count": 1, "reminder_count": 0, "insight": {"kind": "bill_due"},
        })
        self.assertEqual(item.insight, {"kind": "bill_due"})


if __name__ == "__main__":
    unittest.main()
