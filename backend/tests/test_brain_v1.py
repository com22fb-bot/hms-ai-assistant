"""Cerebro v1 (Etapa 1): C1–C10 con BRAIN_V1_ENABLED y equivalencia con la bandera apagada."""
from __future__ import annotations

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


class _Flag:
    def __init__(self, on: bool):
        self.on = on

    def __enter__(self):
        self.old = os.environ.get("BRAIN_V1_ENABLED")
        os.environ["BRAIN_V1_ENABLED"] = "true" if self.on else "false"

    def __exit__(self, *exc):
        if self.old is None:
            os.environ.pop("BRAIN_V1_ENABLED", None)
        else:
            os.environ["BRAIN_V1_ENABLED"] = self.old


class FlagDefaultTests(unittest.TestCase):
    def test_default_off(self):
        from app.services.brain_v1 import brain_v1_enabled

        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("BRAIN_V1_ENABLED", None)
            self.assertFalse(brain_v1_enabled())

    def test_off_keeps_legacy_subject_and_skip(self):
        from app.services.case_engine import normalize_subject
        from app.services.import_categories import skip_message

        with _Flag(False):
            self.assertEqual(normalize_subject("Recordatorio: Factura F-1"), "recordatorio factura f-1")
            self.assertTrue(skip_message(["social"], "security@mail.instagram.com", "Nuevo inicio de sesión"))


class C1SecurityTests(unittest.TestCase):
    def test_security_never_skipped_even_with_social_excluded(self):
        from app.services.import_categories import skip_message

        with _Flag(True):
            self.assertFalse(skip_message(["social"], "security@mail.instagram.com", "Nuevo inicio de sesión en tu cuenta"))
            self.assertFalse(skip_message(["social"], "no-reply@tiktok.com", "Código de verificación de TikTok"))
            self.assertTrue(skip_message(["social"], "noreply@youtube.com", "Nuevo video de Cocina Fácil"))

    def test_protected_types_headers_only(self):
        from app.services.brain_v1.protected import protected_type

        self.assertEqual(protected_type("x@tiktok.com", "Tu código de acceso"), "code")
        self.assertEqual(protected_type("a@buzon-sat.example", "SAT: requerimiento"), "government")
        self.assertEqual(protected_type("a@cfe.example", "Tu recibo CFE"), "invoice")
        self.assertEqual(protected_type("a@clinica.example", "Cita confirmada"), "health")
        self.assertIsNone(protected_type("noreply@youtube.com", "Nuevo video"))


class C2DateTests(unittest.TestCase):
    def setUp(self):
        from app.services.brain_v1.dates import extract_dates

        self.extract = extract_dates

    def test_relative_resolved_in_mexico_city(self):
        r = self.extract("Docs", "Envía tu INE a más tardar el próximo viernes.", "2026-10-12T16:00:00Z")
        self.assertEqual(r.due_at[:10], "2026-10-16")
        # 02:00Z del martes 13 es lunes 12 a las 20:00 en CDMX → mismo viernes 16.
        r = self.extract("Docs", "Envía tu INE a más tardar mañana.", "2026-10-13T02:00:00Z")
        self.assertEqual(r.due_at[:10], "2026-10-13")
        self.assertEqual(self.extract("x", "La renta vence a fin de mes.", "2026-10-12T16:00:00Z").due_at[:10], "2026-10-31")
        self.assertEqual(self.extract("x", "Favor de pagar en 3 días.", "2026-10-12T16:00:00Z").due_at[:10], "2026-10-15")

    def test_due_and_event_are_separate_with_evidence(self):
        r = self.extract("Cita", "Su cita quedó confirmada para el 2026-10-20 a las 10:00.", "2026-10-07T15:00:00Z", kind="appointment")
        self.assertIsNone(r.due_at)
        self.assertEqual(r.event_at, "2026-10-20T10:00:00-06:00")
        self.assertIn("2026-10-20", r.event_evidence)

    def test_never_invent_and_flag_ambiguity(self):
        self.assertIsNone(self.extract("x", "Paga cuanto antes.", "2026-10-07T16:00:00Z").due_at)
        self.assertIsNone(self.extract("x", "Fecha de emisión: 2026-10-01.", "2026-10-07T16:00:00Z").due_at)
        r = self.extract("x", "Favor de pagar el viernes o el lunes.", "2026-10-13T16:00:00Z")
        self.assertIsNone(r.due_at)
        self.assertTrue(r.date_ambiguous)
        r = self.extract("Invoice", "Your invoice is due on 03/04/2027.", "2026-10-13T16:00:00Z")
        self.assertIsNone(r.due_at)
        self.assertTrue(r.date_ambiguous)


class C4DocumentTests(unittest.TestCase):
    def test_doc_key_and_amount(self):
        from app.services.brain_v1.documents import amounts_compatible, extract_amount, extract_doc_token

        self.assertEqual(extract_doc_token("Factura F-1001", ""), "F-1001")
        self.assertEqual(extract_doc_token("Tu pedido", "Pedido #A-555 por $499.00"), "A-555")
        self.assertIsNone(extract_doc_token("Factura de octubre 2026", "Teléfono 5512345678"))
        self.assertEqual(extract_amount("", "por $1,250.00 MXN"), 1250.0)
        self.assertTrue(amounts_compatible(1250.0, 1250.5))
        self.assertFalse(amounts_compatible(1250.0, 625.0))

    def test_reminder_prefixes_stripped_only_with_flag(self):
        from app.services.case_engine import normalize_subject

        with _Flag(True):
            for prefix in ("Recordatorio:", "Reminder:", "Aviso:", "Último aviso:", "RE: Recordatorio:"):
                self.assertEqual(normalize_subject(f"{prefix} Factura F-1"), "factura f-1")


class CorpusAcceptanceTests(unittest.TestCase):
    """Criterios de aceptación de la Etapa 1 sobre tests/brain_corpus (flag ON)."""

    def test_corpus_acceptance(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
        import eval_brain

        with _Flag(True):
            corpus = eval_brain.load_corpus()
            self.assertGreaterEqual(len(corpus), 150)
            metrics = eval_brain.evaluate(corpus, eval_brain.run_pipeline(corpus, True), True)
        self.assertEqual(eval_brain.check(metrics), [], metrics)
        self.assertEqual(sum(r["pasa"] for r in metrics["partd"]), 12)


class C10HeadersFirstTests(unittest.TestCase):
    def test_graph_excluded_message_never_downloads_body(self):
        import app.services.microsoft_import as mi
        from tests.fake_supabase import FakeSupabase

        calls = []

        def graph(_account, url, params=None):
            calls.append(params["$select"])
            mid = url.rsplit("/", 1)[-1]
            sender = {"m1": "noreply@youtube.com", "m2": "security@mail.instagram.com"}[mid]
            subject = {"m1": "Nuevo video", "m2": "Nuevo inicio de sesión en tu cuenta"}[mid]
            return {"id": mid, "subject": subject, "from": {"emailAddress": {"address": sender}}, "body": {"content": "x"}}

        refs = [mi.encode_microsoft_ref("inbox", "m1"), mi.encode_microsoft_ref("inbox", "m2")]
        db = FakeSupabase({})
        with _Flag(True), mock.patch.object(mi, "OAuthStorage", lambda: SimpleNamespace(client=db)), \
                mock.patch.object(mi, "_existing_message_ids", lambda **_: set()), \
                mock.patch.object(mi, "_graph_get_with_refresh", graph), \
                mock.patch.object(mi, "_get_or_create_thread", lambda **_: {"id": "t1"}):
            result = mi.sync_microsoft_page(account={"id": "a1", "email": "u@outlook.com"}, refs=refs, offset=0, exclude=["social"])
        self.assertEqual(result["skipped_excluded"], 1)
        self.assertEqual(calls.count(mi.MICROSOFT_HEADER_SELECT), 2)
        self.assertEqual(calls.count(mi.MICROSOFT_SELECT + mi.MICROSOFT_BRAIN_EXTRA), 1)  # solo la alerta de seguridad baja cuerpo

    def test_imap_excluded_message_never_downloads_body(self):
        import app.services.yahoo_import as yi
        from tests.fake_supabase import FakeSupabase

        specs = []
        heads = {"1": b"From: noreply@youtube.com\r\nSubject: Nuevo video\r\n\r\n",
                 "2": b"From: no-reply@tiktok.com\r\nSubject: Codigo de verificacion de TikTok\r\n\r\n"}

        class Imap:
            def uid(self, _cmd, uid, spec):
                specs.append((uid, spec))
                raw = heads[uid] + (b"cuerpo" if spec != yi.HEADER_ONLY_SPEC else b"")
                return "OK", [(b"1 (FLAGS (\\\\Seen))", raw)]

            def select(self, *_a, **_k):
                return "OK", [b"1"]

            def logout(self):
                return "BYE", []

        db = FakeSupabase({})
        with _Flag(True), mock.patch.object(yi, "OAuthStorage", lambda: SimpleNamespace(client=db)), \
                mock.patch.object(yi, "_existing_message_ids", lambda **_: set()), \
                mock.patch.object(yi, "_prepare_imap_secret", lambda a, p, **_: (a, p)), \
                mock.patch.object(yi, "_open_mailbox_client", lambda *a, **k: Imap()), \
                mock.patch.object(yi, "_select_folder", lambda *a, **k: None):
            refs = [yi.encode_yahoo_ref("INBOX", "1"), yi.encode_yahoo_ref("INBOX", "2")]
            result = yi.sync_yahoo_page(account={"id": "a1", "email": "u@yahoo.com"}, app_password="x", refs=refs,
                                        offset=0, exclude=["social"])
        self.assertEqual(result["skipped_excluded"], 1)
        full = [uid for uid, spec in specs if spec != yi.HEADER_ONLY_SPEC]
        self.assertEqual(full, ["2"])


if __name__ == "__main__":
    unittest.main()


class C4bPeriodTests(unittest.TestCase):
    def test_billing_month_or_received_month(self):
        from app.services.brain_v1.documents import billing_period, period_key

        self.assertEqual(billing_period("Tu recibo de octubre", "", "2026-11-02T16:00:00Z"), ("2026-10", "facturacion"))
        self.assertEqual(billing_period("Aviso de cobro", "Saldo pendiente", "2026-11-02T16:00:00Z"), ("2026-11", "recepcion"))
        self.assertEqual(billing_period("Tu recibo de diciembre", "", "2027-01-03T16:00:00Z"), ("2026-12", "facturacion"))
        # 05:00Z del 1-nov = 31-oct 23:00 en CDMX → mes de recepción octubre
        self.assertEqual(billing_period("Aviso de cobro", "", "2026-11-01T05:00:00Z")[0], "2026-10")
        self.assertNotEqual(period_key("x", "Tu recibo de octubre", "", "2026-10-05T16:00:00Z"),
                            period_key("x", "Tu recibo de noviembre", "", "2026-11-05T16:00:00Z"))


class C5bCrossSenderTests(unittest.TestCase):
    def test_brand_mentioned_ignores_generic_words(self):
        from app.services.brain_v1.documents import brand_mentioned

        self.assertTrue(brand_mentioned("aguadelvalle", "Pago aplicado: servicio AGUADELVALLE por $512.00"))
        self.assertTrue(brand_mentioned("gasolinera-roja", "Pago a GASOLINERA ROJA"))
        self.assertFalse(brand_mentioned("cobros-pagos", "Pago aplicado a cobros"))

    def test_corpus_cross_sender_never_auto_resolves(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
        import eval_brain

        with _Flag(True):
            corpus = eval_brain.load_corpus()
            metrics = eval_brain.evaluate(corpus, eval_brain.run_pipeline(corpus, True), True)
        self.assertEqual(metrics["cross_sender_auto_closed"], 0)
        self.assertEqual(metrics["possible_payment_ok"], "2/2")
