"""Cerebro v1 Etapa 1.2 (adenda de ASTRA): A1–A11 con redacciones distintas a las del lote ciego."""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault("OAUTH_ENCRYPTION_KEY", "test-oauth-encryption-key-32chars!!")


def msg(mid, sender, subject, body, received, labels=None, direction="inbound", headers=None, thread=None):
    return {"id": mid, "thread_id": thread or f"t-{mid}", "account_id": "A", "external_message_id": mid, "sender": sender,
            "recipients": [{"email": "yo@correo.example"}], "cc": [], "bcc": [], "subject": subject, "body_text": body,
            "snippet": body[:200], "received_at": received, "labels": (labels or []) + (["SENT"] if direction == "outbound" else ["INBOX"]),
            "headers": headers or {}, "is_unread": True, "direction": direction, "case_processed": False}


def run(messages, verified=True):
    from tests.fake_supabase import FakeSupabase, _Query
    from app.services.brain_v1.engine import classify_pending_messages_v1

    if not hasattr(_Query, "gte"):
        _Query.gte = lambda self, *_a: self  # type: ignore[attr-defined]
    db = FakeSupabase({"communication_accounts": [{"id": "A", "workspace_id": "W"}], "communication_messages": list(messages),
                       "intelligent_cases": [], "case_messages": [], "case_events": [], "case_participants": [],
                       "learning_patterns": [], "organizational_patterns": []})
    classify_pending_messages_v1(client=db, account_id="A", workspace_id="W", messages=list(messages), user_verified=verified)
    links = {x["message_id"]: x["case_id"] for x in db.tables["case_messages"]}
    cases = {c["id"]: c for c in db.tables["intelligent_cases"]}
    msgs = {m["id"]: m for m in db.tables["communication_messages"]}
    return db, links, cases, msgs


def analyze(sender, subject, body, received="2026-10-12T16:00:00Z", **kw):
    from app.services.brain_v1.analyzer import analyze as _a

    return _a(msg("x", sender, subject, body, received, **kw))


class A1A2SecurityTests(unittest.TestCase):
    def test_password_change_from_social_is_protected(self):
        from app.services.brain_v1.protected import is_security_or_code
        from app.services.import_categories import skip_message

        self.assertEqual(is_security_or_code("no-reply@redsocial.example", "Actualizaste tu contraseña", "Tu contraseña se actualizó hoy."), "security")
        self.assertEqual(is_security_or_code("x@y.example", "Your password was changed", ""), "security")
        a = analyze("no-reply@redsocial.example", "Restableciste tu contraseña", "Listo.", labels=["CATEGORY_SOCIAL"])
        self.assertEqual((a.rule, a.triage), ("security", "notice"))
        os.environ["BRAIN_V1_ENABLED"] = "true"
        try:
            self.assertFalse(skip_message(["social"], "no-reply@redsocial.example", "Restableciste tu contraseña", ["CATEGORY_SOCIAL"]))
        finally:
            os.environ.pop("BRAIN_V1_ENABLED", None)

    def test_security_with_action_is_n1_case(self):
        db, links, cases, _ = run([msg("s1", "seguridad@correo-web.example", "Acceso bloqueado",
                                       "Alguien tiene tu contraseña. Cambia tu contraseña ahora.", "2026-10-12T16:00:00Z")])
        self.assertIn("s1", links)
        self.assertEqual(cases[links["s1"]]["priority"], "critical")

    def test_conditional_security_stays_notice(self):
        a = analyze("seguridad@app.example", "Nuevo inicio de sesión", "Detectamos un inicio de sesión desde Puebla. Si no fuiste tú, cambia tu contraseña.")
        self.assertEqual((a.rule, a.actionable), ("security", False))


class A3PhishingTests(unittest.TestCase):
    def test_brand_mismatch_with_payment_request_goes_to_review(self):
        a = analyze("avisos@seguridad-cuentas.example", "Tu tarjeta BBVA fue bloqueada", "Ingresa tus datos en este link en menos de 24 horas.")
        self.assertEqual((a.rule, a.triage, a.actionable), ("phishing_suspect", "review", False))
        self.assertLess(a.confidence, 0.5)
        self.assertIsNone(a.protected)

    def test_real_brand_domain_is_not_phishing(self):
        a = analyze("alertas@bbva.example", "Tu tarjeta BBVA fue bloqueada", "Ingresa a la app oficial en menos de 24 horas.")
        self.assertNotEqual(a.rule, "phishing_suspect")

    def test_mention_without_request_is_not_phishing(self):
        a = analyze("noticias@periodico.example", "Banorte abre sucursal", "La nueva sucursal abre el lunes.")
        self.assertNotEqual(a.rule, "phishing_suspect")


class A4FolioTests(unittest.TestCase):
    def test_folio_after_brand_word_in_subject(self):
        from app.services.brain_v1.documents import doc_key

        self.assertEqual(doc_key("gasnat", "Recibo Gas Natural No. GN-55120", "Total $300. Vence el 30/10/2026."), "gasnat:GN-55120")
        self.assertEqual(doc_key("acme", "Invoice ACME # 7781", "Due soon."), "acme:7781")

    def test_invoice_reminder_payment_single_case(self):
        S = "cobros@internet-sur.example"
        _, links, cases, _ = run([
            msg("i1", S, "Factura Internet Sur No. IS-4410", "Total $450.00. Vence el 25/10/2026.", "2026-10-02T16:00:00Z"),
            msg("i2", S, "Recordatorio: factura IS-4410", "Tu factura IS-4410 por $450.00 vence pronto. Favor de pagar.", "2026-10-20T16:00:00Z"),
            msg("i3", S, "Recibimos tu pago IS-4410", "Confirmamos el pago de $450.00 de la factura IS-4410.", "2026-10-21T16:00:00Z"),
        ])
        self.assertEqual(len({links["i1"], links["i2"], links["i3"]}), 1)
        case = cases[links["i1"]]
        self.assertEqual(case["status"], "resolved")
        # A11: resuelto → N3, con la prioridad máxima en metadata
        self.assertEqual(case["priority"], "low")
        self.assertIn(case["metadata"]["priority_max"], {"normal", "high", "critical"})


class A5PaymentTests(unittest.TestCase):
    def test_bank_payment_wording_triggers_possible_payment(self):
        _, links, cases, _ = run([
            msg("b1", "facturas@aguas-norte.example", "Recibo Aguas Norte", "Total a pagar $380.00. Fecha límite de pago: 28 de octubre de 2026.", "2026-10-05T16:00:00Z"),
            msg("b2", "avisos@banco-sol.example", "Pago de servicio procesado", "Se procesó el pago a AGUAS NORTE por $380.00 con tu tarjeta.", "2026-10-07T16:00:00Z"),
        ])
        self.assertEqual(links.get("b2"), links["b1"])
        case = cases[links["b1"]]
        self.assertNotIn(case["status"], {"resolved", "closed"})
        self.assertEqual(case["metadata"]["payment_status"], "possible")

    def test_rejected_payment_is_not_confirmation(self):
        a = analyze("pagos@tienda.example", "Tu pago fue rechazado", "El pago realizado con tu tarjeta fue rechazado.")
        self.assertNotIn(a.rule, {"payment_confirmation", "partial_payment"})

    def test_abono_word_is_not_negation(self):
        a = analyze("cxc@proveedor.example", "Abono recibido FX-901", "Recibimos un abono de $100.00 a la factura FX-901. Saldo pendiente: $50.00.")
        self.assertEqual(a.rule, "partial_payment")


class A6DateInvariantTests(unittest.TestCase):
    def test_update_never_nulls_existing_due(self):
        S = "admin@escuela.example"
        _, links, cases, _ = run([
            msg("d1", S, "Colegiatura folio CE-77", "Favor de pagar la colegiatura folio CE-77 por $2,000.00 a más tardar el 30 de octubre.", "2026-10-05T16:00:00Z"),
            msg("d2", S, "Abono a colegiatura CE-77", "Recibimos un abono de $500.00 al folio CE-77. Saldo pendiente $1,500.00.", "2026-10-09T16:00:00Z"),
        ])
        self.assertEqual(links["d1"], links["d2"])
        self.assertTrue(cases[links["d1"]]["due_at"].startswith("2026-10-30"))

    def test_no_null_helper(self):
        from app.services.brain_v1.engine import _no_null_dates

        out = _no_null_dates({"due_at": None, "event_at": None, "metadata": {"event_at": None}},
                             {"due_at": "2026-10-30", "event_at": "2026-10-20", "metadata": {"event_at": "2026-10-20"}})
        self.assertNotIn("due_at", out)
        self.assertNotIn("event_at", out)
        self.assertEqual(out["metadata"]["event_at"], "2026-10-20")


class A7VerificationTests(unittest.TestCase):
    def test_codes_never_open_case(self):
        a = analyze("seguridad@chat.example", "Tu código de acceso es 449120", "Usa este código para confirmar tu cuenta.")
        self.assertEqual((a.rule, a.actionable), ("security", False))

    def test_third_party_verifications_group_in_no_action(self):
        S = "hola@app-notas.example"
        _, links, cases, _ = run([msg(f"v{i}", S, "Verifica tu correo", "Verifica tu correo para activar tu cuenta.", f"2026-10-0{i+1}T16:00:00Z") for i in range(3)])
        self.assertEqual(len({links[f"v{i}"] for i in range(3)}), 1)
        self.assertEqual(cases[links["v0"]]["status"], "no_action")


class A8OutboundWaitTests(unittest.TestCase):
    def test_outbound_wait_with_date_opens_waiting_case(self):
        _, links, cases, msgs = run([msg("o1", "yo@correo.example", "Propuesta de mantenimiento",
                                         "Gracias. Espero su propuesta para el jueves.", "2026-10-12T16:00:00Z", direction="outbound")])
        case = cases[links["o1"]]
        self.assertEqual(case["status"], "waiting_external")
        self.assertTrue(case["due_at"].startswith("2026-10-15"))
        self.assertEqual(msgs["o1"]["triage_category"], "waiting_external")

    def test_outbound_without_wait_does_not_open(self):
        _, links, _, _ = run([msg("o2", "yo@correo.example", "Hola", "Te mando el archivo el jueves.", "2026-10-12T16:00:00Z", direction="outbound")])
        self.assertNotIn("o2", links)


class A9DateFormatTests(unittest.TestCase):
    def test_weekday_plus_date_and_time(self):
        from app.services.brain_v1.dates import extract_dates

        r = extract_dates("Cita confirmada", "Te esperamos el miércoles 21 de octubre a las 16:45.", "2026-10-12T16:00:00Z", kind="appointment")
        self.assertEqual(r.event_at, "2026-10-21T16:45:00-06:00")
        r = extract_dates("Reunión", "La reunión es el viernes, 23 de octubre de 2026 a las 8:00 de la noche.", "2026-10-12T16:00:00Z", kind="event")
        self.assertEqual(r.event_at, "2026-10-23T20:00:00-06:00")
        r = extract_dates("Webinar Ventas", "Lunes 26 de octubre de 2026, 18:00 hora CDMX.", "2026-10-12T16:00:00Z", kind="event")
        self.assertEqual(r.event_at, "2026-10-26T18:00:00-06:00")

    def test_weekday_that_contradicts_date_is_ambiguous(self):
        from app.services.brain_v1.dates import extract_dates

        r = extract_dates("Cita", "Tu cita es el lunes 21 de octubre a las 10:00.", "2026-10-12T16:00:00Z", kind="appointment")
        self.assertIsNone(r.event_at)
        self.assertTrue(r.date_ambiguous)

    def test_de_la_manana_is_not_tomorrow_and_reschedule_moves_case(self):
        S = "agenda@consultorio-luz.example"
        _, links, cases, _ = run([
            msg("c1", S, "Cita confirmada", "Tu consulta está confirmada para el lunes 19 de octubre a las 12:00.", "2026-10-12T16:00:00Z"),
            msg("c2", S, "Cita reprogramada", "Tu cita fue reprogramada al martes 27 de octubre a las 8:30 de la mañana.", "2026-10-14T16:00:00Z"),
        ])
        self.assertEqual(links["c1"], links["c2"])
        case = cases[links["c1"]]
        self.assertEqual(case["status"], "scheduled")
        self.assertTrue(str(case["event_at"]).startswith("2026-10-27T08:30"))


class A10BulkHeaderTests(unittest.TestCase):
    def test_list_unsubscribe_blocks_request(self):
        body = "Por favor envía tus comentarios sobre la nueva función."
        plain = analyze("equipo@producto.example", "Tu opinion", body)
        bulk = analyze("equipo@producto.example", "Tu opinion", body, headers={"List-Unsubscribe": "<mailto:baja@producto.example>"})
        self.assertEqual(plain.rule, "request")
        self.assertNotEqual(bulk.rule, "request")
        self.assertFalse(bulk.actionable)
        self.assertTrue(bulk.bulk)

    def test_list_id_counts_and_real_bill_still_actionable(self):
        a = analyze("recibos@luz.example", "Tu recibo de luz", "Total a pagar $500.00. Fecha límite de pago: 30 de octubre de 2026.",
                    headers={"List-Id": "<recibos.luz.example>"})
        self.assertTrue(a.bulk)
        self.assertTrue(a.actionable)


if __name__ == "__main__":
    unittest.main()
