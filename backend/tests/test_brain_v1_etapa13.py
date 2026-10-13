"""Cerebro v1 Etapa 1.3 (adenda 1.3 de ASTRA): A12–A15 con redacciones distintas a las de los lotes."""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault("OAUTH_ENCRYPTION_KEY", "test-oauth-encryption-key-32chars!!")

from tests.test_brain_v1_etapa12 import analyze, msg, run  # noqa: E402


class A12BookingTests(unittest.TestCase):
    def test_automated_booking_with_date_is_scheduled(self):
        _, links, cases, _ = run([msg("h1", "reservaciones@hotel-sierra.example", "Tu reservación está confirmada",
                                      "Check-in: sábado 7 de noviembre de 2026. Check-out: lunes 9 de noviembre.", "2026-10-12T16:00:00Z")])
        case = cases[links["h1"]]
        self.assertEqual(case["status"], "scheduled")
        self.assertTrue(str(case["event_at"]).startswith("2026-11-07"))
        self.assertEqual(case["priority"], "low")

    def test_registration_from_person_is_not_booking(self):
        a = analyze("pedro@amigos.example", "Registro confirmado", "Ya quedó tu registro confirmado para el 3 de noviembre, ¿vienes?")
        self.assertNotEqual(a.rule, "booking")

    def test_booking_without_date_is_not_case(self):
        a = analyze("booking@vuelos-sur.example", "Your booking is confirmed", "Thanks for flying with us.")
        self.assertNotEqual(a.rule, "booking")

    def test_date_range_starts_first_day(self):
        from app.services.brain_v1.dates import extract_dates

        r = extract_dates("Reservación confirmada", "Tu estancia del 4 al 6 de diciembre.", "2026-10-12T16:00:00Z", kind="booking")
        self.assertTrue(r.event_at.startswith("2026-12-04"))


class A13AutoNoticeTests(unittest.TestCase):
    def test_order_shipped_is_informational(self):
        a = analyze("pedidos@tienda-norte.example", "Tu pedido fue enviado", "Tu pedido 7781 va en camino.")
        self.assertEqual((a.triage, a.actionable), ("informational", False))

    def test_order_with_action_is_not_swallowed(self):
        a = analyze("pedidos@tienda-norte.example", "Problema con tu pedido", "Tu pedido fue enviado pero el pago fue rechazado; actualiza tu tarjeta.")
        self.assertNotEqual(a.rule, "auto_notice")

    def test_card_charge_is_protected_bank_notice(self):
        a = analyze("alertas@banco-luna.example", "Compra con tu tarjeta", "Se realizó un cargo de $250.00 en Farmacia Sol.")
        self.assertEqual((a.triage, a.protected), ("notice", "bank"))

    def test_results_and_renewal(self):
        a = analyze("no-reply@lab-central.example", "Resultados", "Tus resultados ya están disponibles en línea.")
        self.assertEqual((a.triage, a.protected), ("notice", "health"))
        a = analyze("cuentas@nube-x.example", "Tu plan", "Tu plan se renovará automáticamente el 2 de diciembre.")
        self.assertEqual((a.triage, a.actionable), ("notice", False))

    def test_personal_sender_not_auto_notice(self):
        a = analyze("laura@empresa.example", "Tu pedido fue enviado", "Te aviso que tu pedido fue enviado, ¿lo confirmas?")
        self.assertNotEqual(a.rule, "auto_notice")


class A14ScheduledPriorityTests(unittest.TestCase):
    def test_scheduled_n3_and_n2_within_three_days(self):
        from app.services.brain_v1.engine import _scheduled_priority

        self.assertEqual(_scheduled_priority("2026-10-30T10:00:00-06:00", "2026-10-12T16:00:00+00:00"), "low")
        self.assertEqual(_scheduled_priority("2026-10-14T10:00:00-06:00", "2026-10-12T16:00:00+00:00"), "normal")
        self.assertEqual(_scheduled_priority(None, "2026-10-12T16:00:00+00:00"), "low")

    def test_appointment_never_n1(self):
        _, links, cases, _ = run([msg("a1", "citas@clinica-norte.example", "Cita confirmada",
                                      "Tu cita está confirmada para hoy a las 18:00.", "2026-10-12T16:00:00Z")])
        self.assertEqual(cases[links["a1"]]["priority"], "normal")


class A15PhishingSafetyTests(unittest.TestCase):
    def setUp(self):
        os.environ["BRAIN_V1_ENABLED"] = "true"

    def tearDown(self):
        os.environ.pop("BRAIN_V1_ENABLED", None)

    def test_processor_mentioning_merchant_is_not_phishing(self):
        a = analyze("avisos@procesador-pagos.example", "Pagaste en Coppel", "Pago aprobado de $800.00 en Coppel. Ver detalle de la operación.")
        self.assertNotEqual(a.rule, "phishing_suspect")

    def test_family_forward_with_link_is_not_phishing(self):
        a = analyze("tio@familia.example", "Fwd: Invoice 3310", "Can you pay this? --- Invoice No. 3310. Amount due: USD 40.00. Due November 20, 2026. Click here to pay.")
        self.assertNotEqual(a.rule, "phishing_suspect")

    def test_suspect_only_goes_to_review_never_hidden(self):
        from app.services.import_categories import skip_message

        sender, subject = "promos@ofertas-mundo.example", "Netflix: actualiza tus datos hoy"
        a = analyze(sender, subject, "Tu cuenta se suspenderá. Ingresa tus datos en este enlace.", labels=["CATEGORY_PROMOTIONS"])
        self.assertEqual(a.triage, "review")
        self.assertFalse(skip_message(["promos", "social"], sender, subject, ["CATEGORY_PROMOTIONS"]))
        _, links, _, msgs = run([msg("p1", sender, subject, "Tu cuenta se suspenderá. Ingresa tus datos en este enlace.",
                                     "2026-10-12T16:00:00Z", labels=["CATEGORY_PROMOTIONS"])])
        self.assertEqual(msgs["p1"]["triage_category"], "review")
        self.assertNotIn("p1", links)


if __name__ == "__main__":
    unittest.main()
