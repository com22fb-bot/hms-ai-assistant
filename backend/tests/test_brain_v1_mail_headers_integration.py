"""PR #128: pruebas de integración por proveedor (Gmail, Graph, IMAP) con el insert real de cada importador.

Con BRAIN_V1_ENABLED: communication_messages.mail_headers se escribe. Con la bandera apagada: la llave no existe.
List-Unsubscribe nunca convierte un mensaje en confiable (phishing y seguridad se evalúan antes que "masivo").
"""
from __future__ import annotations

import base64
import json
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault("OAUTH_ENCRYPTION_KEY", "test-oauth-encryption-key-32chars!!")

from tests.test_brain_v1 import _Flag  # noqa: E402

LU = "<mailto:baja@tienda.example>, <https://tienda.example/baja>"


def _inserted(db):
    return db.tables.get("communication_messages", [])


class _Exec:
    def __init__(self, value):
        self.value = value

    def execute(self):
        return self.value


class _GmailMessages:
    def list(self, **_k):
        return _Exec({"messages": [{"id": "g1"}]})

    def get(self, **_k):
        body = base64.urlsafe_b64encode(b"Ofertas de la semana").decode()
        return _Exec({"id": "g1", "threadId": "th1", "labelIds": ["INBOX", "CATEGORY_PROMOTIONS"], "snippet": "Ofertas",
                      "internalDate": "1791900000000",
                      "payload": {"mimeType": "text/plain", "body": {"data": body}, "headers": [
                          {"name": "From", "value": "Tienda <promo@tienda.example>"}, {"name": "To", "value": "u@gmail.com"},
                          {"name": "Subject", "value": "Ofertas"}, {"name": "Date", "value": "Tue, 13 Oct 2026 10:00:00 -0600"},
                          {"name": "List-Unsubscribe", "value": LU}, {"name": "List-Id", "value": "Promos <promos.tienda.example>"}]}})


class _GmailService:
    def users(self):
        return SimpleNamespace(messages=lambda: _GmailMessages())


def _run_gmail(flag_on: bool):
    import app.services.gmail_full_sync as gs
    from tests.fake_supabase import FakeSupabase

    db = FakeSupabase({})
    storage = SimpleNamespace(client=db, get_account=lambda _id: {"id": "a1", "email": "u@gmail.com"})
    with _Flag(flag_on), mock.patch.object(gs, "OAuthStorage", lambda: storage), \
            mock.patch.object(gs, "build", lambda *a, **k: _GmailService()), \
            mock.patch.object(gs, "_existing_message_ids", lambda **_: set()), \
            mock.patch.object(gs, "_get_or_create_thread", lambda **_: {"id": "t1"}):
        result = gs.sync_gmail_page(credentials=None, account_id="a1")
    return result, _inserted(db)


def _run_graph(flag_on: bool):
    import app.services.microsoft_import as mi
    from tests.fake_supabase import FakeSupabase

    selects = []

    def graph(_account, url, params=None):
        selects.append(params["$select"])
        return {"id": "m1", "subject": "Boletín", "from": {"emailAddress": {"address": "news@contoso.example"}},
                "body": {"contentType": "text", "content": "Novedades"}, "receivedDateTime": "2026-10-13T16:00:00Z",
                "isRead": False, "conversationId": "c1", "categories": ["Azul"], "inferenceClassification": "other",
                "internetMessageHeaders": [{"name": "List-Unsubscribe", "value": LU}, {"name": "List-Id", "value": "news.contoso.example"}]}

    db = FakeSupabase({})
    with _Flag(flag_on), mock.patch.object(mi, "OAuthStorage", lambda: SimpleNamespace(client=db)), \
            mock.patch.object(mi, "_existing_message_ids", lambda **_: set()), \
            mock.patch.object(mi, "_graph_get_with_refresh", graph), \
            mock.patch.object(mi, "_get_or_create_thread", lambda **_: {"id": "t1"}):
        result = mi.sync_microsoft_page(account={"id": "a1", "email": "u@outlook.com"},
                                        refs=[mi.encode_microsoft_ref("inbox", "m1")], offset=0, exclude=[])
    return result, _inserted(db), selects


def _run_imap(flag_on: bool):
    import app.services.yahoo_import as yi
    from tests.fake_supabase import FakeSupabase

    raw = (b"From: news@lista.example\r\nTo: u@yahoo.com\r\nSubject: Boletin\r\nDate: Tue, 13 Oct 2026 10:00:00 -0600\r\n"
           b"List-Unsubscribe: <mailto:baja@lista.example>\r\nList-ID: <boletin.lista.example>\r\n\r\nNovedades")

    class Imap:
        def uid(self, _cmd, _uid, _spec):
            return "OK", [(b"1 (FLAGS (\\\\Seen))", raw)]

        def select(self, *_a, **_k):
            return "OK", [b"1"]

        def logout(self):
            return "BYE", []

    db = FakeSupabase({})
    with _Flag(flag_on), mock.patch.object(yi, "OAuthStorage", lambda: SimpleNamespace(client=db)), \
            mock.patch.object(yi, "_existing_message_ids", lambda **_: set()), \
            mock.patch.object(yi, "_prepare_imap_secret", lambda a, p, **_: (a, p)), \
            mock.patch.object(yi, "_open_mailbox_client", lambda *a, **k: Imap()), \
            mock.patch.object(yi, "_select_folder", lambda *a, **k: None):
        result = yi.sync_yahoo_page(account={"id": "a1", "email": "u@yahoo.com"}, app_password="x",
                                    refs=[yi.encode_yahoo_ref("Bulk", "1")], offset=0, exclude=[])
    return result, _inserted(db)


class GmailIntegrationTests(unittest.TestCase):
    def test_flag_on_stores_headers_and_labels(self):
        _, rows = _run_gmail(True)
        self.assertEqual(len(rows), 1)
        h = rows[0]["mail_headers"]
        self.assertEqual(h["list_unsubscribe"], LU)
        self.assertEqual(h["list_id"], "Promos <promos.tienda.example>")
        self.assertEqual(h["provider_labels"], ["INBOX", "CATEGORY_PROMOTIONS"])
        self.assertEqual(h["source"], "gmail")

    def test_flag_off_insert_unchanged(self):
        _, rows = _run_gmail(False)
        self.assertEqual(len(rows), 1)
        self.assertNotIn("mail_headers", rows[0])


class GraphIntegrationTests(unittest.TestCase):
    def test_flag_on_stores_headers_and_labels(self):
        _, rows, selects = _run_graph(True)
        self.assertEqual(rows[0]["mail_headers"]["list_id"], "news.contoso.example")
        self.assertEqual(rows[0]["mail_headers"]["provider_labels"], ["Azul", "inference:other"])
        self.assertTrue(all("internetMessageHeaders" in s for s in selects))

    def test_flag_off_insert_and_select_unchanged(self):
        import app.services.microsoft_import as mi

        _, rows, selects = _run_graph(False)
        self.assertNotIn("mail_headers", rows[0])
        self.assertEqual(selects, [mi.MICROSOFT_SELECT])


class ImapIntegrationTests(unittest.TestCase):
    def test_flag_on_stores_headers_and_folder(self):
        _, rows = _run_imap(True)
        h = rows[0]["mail_headers"]
        self.assertEqual(h["list_unsubscribe"], "<mailto:baja@lista.example>")
        self.assertEqual(h["list_id"], "<boletin.lista.example>")
        self.assertIn("folder:Bulk", h["provider_labels"])

    def test_flag_off_insert_unchanged(self):
        _, rows = _run_imap(False)
        self.assertNotIn("mail_headers", rows[0])


class NeverTrustedTests(unittest.TestCase):
    def _analyze(self, sender, subject, body):
        from app.services.brain_v1.analyzer import analyze

        return analyze({"id": "x", "thread_id": "t", "sender": sender, "subject": subject, "body_text": body,
                        "received_at": "2026-10-13T16:00:00Z", "labels": ["INBOX"], "direction": "inbound",
                        "headers": {"list-unsubscribe": LU, "list-id": "lista.example"}})

    def test_phishing_with_list_unsubscribe_still_goes_to_review(self):
        a = self._analyze("avisos@promo-ofertas.example", "PayPal: cuenta suspendida",
                          "Verifica tu identidad en este enlace o tu cuenta será suspendida.")
        self.assertEqual(a.rule, "phishing_suspect")
        self.assertEqual(a.triage, "review")

    def test_security_alert_with_list_unsubscribe_is_protected(self):
        a = self._analyze("no-reply@servicio.example", "Nuevo inicio de sesión", "Detectamos un nuevo inicio de sesión desde un dispositivo no reconocido.")
        self.assertEqual(a.rule, "security")
        self.assertTrue(a.protected)

    def test_bulk_invoice_with_list_unsubscribe_keeps_obligation(self):
        a = self._analyze("facturas@luz.example", "Tu factura", "Total $300.00. Vence: 30/11/2026.")
        self.assertTrue(a.actionable)

    def test_stored_mail_headers_reach_the_brain(self):
        from app.services.brain_v1.analyzer import analyze

        a = analyze({"id": "y", "thread_id": "t", "sender": "news@lista.example", "subject": "Novedades de la semana",
                     "body_text": "Lee nuestras novedades.", "received_at": "2026-10-13T16:00:00Z", "labels": ["INBOX"],
                     "direction": "inbound", "mail_headers": {"list_unsubscribe": LU, "list_id": None}})
        self.assertTrue(a.bulk)

    def test_storage_is_bounded(self):
        from app.services.brain_v1.headers import gmail_mail_headers

        h = gmail_mail_headers([{"name": "List-Unsubscribe", "value": "x" * 10000}], [f"L{i}" * 50 for i in range(100)])
        self.assertLessEqual(len(json.dumps(h)), 512 + 30 * 104 + 200)


if __name__ == "__main__":
    unittest.main()
