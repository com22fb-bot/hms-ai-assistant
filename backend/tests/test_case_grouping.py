import os
import unittest

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault("OAUTH_ENCRYPTION_KEY", "test-oauth-encryption-key-32chars!!")

from app.services import case_engine as ce


class _Q:
    def __init__(self, log): self.log, self.f = log, []
    def select(self, *_): return self
    def eq(self, c, v): self.f.append(("eq", c, v)); return self
    def in_(self, c, v): return self
    def gte(self, c, v): self.f.append(("gte", c, v)); return self
    def order(self, *_a, **_k): return self
    def limit(self, *_): return self
    def execute(self):
        self.log.append(self.f)
        hit = ("eq", "metadata->>event_key", "google:security_alert") in self.f
        return type("R", (), {"data": [{"id": "case-1"}] if hit else []})()


class _C:
    def __init__(self): self.log = []
    def table(self, _): return _Q(self.log)


class EventKeyTests(unittest.TestCase):
    def test_brand(self):
        self.assertEqual(ce.brand_of_email("no-reply@accounts.google.com"), "google")
        self.assertEqual(ce.brand_of_email("noreply@google.com"), "google")
        self.assertEqual(ce.brand_of_email("avisos@e.bbva.com.mx"), "bbva")

    def test_keys(self):
        self.assertEqual(ce.event_key_for("no-reply@accounts.google.com", "Alerta de seguridad"), ("google:security_alert", 7))
        self.assertEqual(ce.event_key_for("no-reply@accounts.google.com", "Alerta de seguridad para hmcelinfo@gmail.com"), ("google:security_alert", 7))
        self.assertEqual(ce.event_key_for("noreply@google.com", "Código de verificación de Google"), ("google:verification_code", 1))
        self.assertIsNone(ce.event_key_for("ventas@tienda.com", "Tu pedido"))

    def test_mask(self):
        self.assertEqual(ce.mask_codes("Tu código es 482913."), "Tu código es ••••••.")
        self.assertEqual(ce.mask_codes("Pedido 2026-10-10"), "Pedido 2026-10-10")

    def test_lookup_is_workspace_scoped_by_event(self):
        client = _C()
        found = ce._find_case_for_message(client=client, account_id="acc-yahoo", thread_id=None,
                                          normalized_subject="alerta de seguridad para x",
                                          workspace_id="ws-1", event_key="google:security_alert",
                                          received_at="2026-10-09T10:00:00+00:00", window_days=7)
        self.assertEqual(found, {"id": "case-1"})
        q = client.log[0]
        self.assertIn(("eq", "workspace_id", "ws-1"), q)
        self.assertNotIn(("eq", "account_id", "acc-yahoo"), q)
        self.assertTrue(any(f[0] == "gte" for f in q))


if __name__ == "__main__":
    unittest.main()
