"""Políticas post lote 3 (redacción general; ningún caso del lote sellado se copia aquí)."""
from __future__ import annotations

import unittest

from tests.test_brain_v1_etapa12 import analyze, msg, run

R = "2026-03-02T15:00:00Z"


class SecurityPolicyTests(unittest.TestCase):
    def test_locked_account_reliable_sender_is_visible_normal_case(self):
        a = analyze("seguridad@banco-norte.example", "Bloqueamos tu cuenta",
                    "Por varios intentos fallidos bloqueamos tu cuenta. Entra a la app para desbloquearla.", R)
        self.assertEqual((a.rule, a.actionable), ("security_action", True))
        _, links, cases, _ = run([msg("s1", "seguridad@banco-norte.example", "Bloqueamos tu cuenta",
                                      "Por varios intentos fallidos bloqueamos tu cuenta. Entra a la app para desbloquearla.", R)])
        case = cases[links["s1"]]
        self.assertEqual(case["priority"], "normal")

    def test_critical_needs_explicit_urgency_and_risk(self):
        a = analyze("security@cloudapp.example", "Unauthorized sign-in",
                    "We detected unauthorized access to your account. Change your password immediately.", R)
        self.assertEqual(a.severity, "critical")
        b = analyze("security@cloudapp.example", "Account locked",
                    "Your account has been locked after several attempts. Unlock it from settings.", R)
        self.assertNotEqual(b.severity, "critical")

    def test_if_not_you_is_never_hidden(self):
        a = analyze("no-reply@tienda-uno.example", "Nuevo inicio de sesión",
                    "Detectamos un inicio de sesión nuevo. Si no fuiste tú, protege tu cuenta desde ajustes.", R)
        self.assertTrue(a.actionable)
        self.assertNotEqual(a.triage, "informational")

    def test_credential_request_goes_to_review(self):
        a = analyze("avisos@servicio-dos.example", "Cuenta suspendida",
                    "Tu cuenta suspendida se reactiva si ingresas tu contraseña y tu NIP en el formulario.", R)
        self.assertEqual(a.triage, "review")
        _, links, cases, _ = run([msg("s9", "avisos@servicio-dos.example", "Cuenta suspendida",
                                      "Tu cuenta suspendida se reactiva si ingresas tu contraseña y tu NIP en el formulario, de inmediato.", R)])
        case = cases[links["s9"]]
        self.assertEqual((case["status"], case["priority"]), ("needs_review", "normal"))


class BillPolicyTests(unittest.TestCase):
    def test_bill_without_deadline_has_no_due_date(self):
        body = "Tu recibo de marzo ya está disponible. Total a pagar: $1,240.00 MXN. Número de cuenta 55120."
        a = analyze("facturacion@luz-ejemplo.example", "Tu recibo de marzo", body, R)
        self.assertIn(a.rule, {"bill_followup", "invoice_due"})
        self.assertIsNone(a.dates.due_at)
        _, links, cases, _ = run([msg("b1", "facturacion@luz-ejemplo.example", "Tu recibo de marzo", body, R)])
        case = cases[links["b1"]]
        self.assertIsNone(case.get("due_at"))

    def test_bill_without_demand_or_deadline_is_followup_case(self):
        body = "Ya puedes consultar tu estado de cuenta de marzo. Importe del periodo: $2,310.50 MXN."
        a = analyze("estados@tarjeta-ejemplo.example", "Estado de cuenta de marzo", body, R)
        self.assertEqual(a.rule, "bill_followup")
        self.assertIsNone(a.dates.due_at)
        _, links, cases, _ = run([msg("b2", "estados@tarjeta-ejemplo.example", "Estado de cuenta de marzo", body, R)])
        self.assertEqual(cases[links["b2"]]["status"], "needs_review")
        self.assertIsNone(cases[links["b2"]].get("due_at"))

    def test_settled_bill_stays_informational(self):
        a = analyze("facturacion@luz-ejemplo.example", "Tu recibo de marzo",
                    "Tu recibo de marzo por $800.00 MXN está domiciliado; no se requiere pago.", R)
        self.assertNotEqual(a.rule, "bill_followup")


class BookingPolicyTests(unittest.TestCase):
    def test_firm_flight_lodging_tickets(self):
        cases = [
            ("reservaciones@aerolinea.example", "Tu vuelo está confirmado", "Tu vuelo está confirmado para el 20 de marzo de 2026 a las 09:15."),
            ("reservations@hotel.example", "Your stay is confirmed", "Your stay is confirmed. Check-in March 21, 2026."),
            ("tickets@eventos.example", "Tus entradas están confirmadas", "Tus entradas están confirmadas para el 28 de marzo de 2026."),
        ]
        for sender, subject, body in cases:
            self.assertEqual(analyze(sender, subject, body, R).rule, "booking", subject)

    def test_request_proposal_cancellation_are_not_bookings(self):
        for body in ["Recibimos tu solicitud de reserva para el 20 de marzo de 2026; tu vuelo está confirmado al pagar.",
                     "Your booking is cancelled. Reservation confirmed on March 20, 2026 has been canceled.",
                     "Propuesta: tu hospedaje está confirmado solo si aceptas antes del 20 de marzo de 2026."]:
            self.assertNotEqual(analyze("reservas@viajes.example", "Reserva", body, R).rule, "booking", body)


class RenewalAndPaymentTests(unittest.TestCase):
    def test_past_renewal_is_informational(self):
        a = analyze("billing@streaming.example", "Subscription renewed",
                    "Your plan was renewed successfully. It will auto-renew next year.", R)
        self.assertEqual((a.triage, a.actionable), ("notice", False))

    def test_previous_payment_never_confirms(self):
        a = analyze("facturacion@agua-ejemplo.example", "Nuevo recibo",
                    "Gracias por tu pago anterior. Tu nuevo recibo es por $310.00 y vence el 25 de marzo de 2026.", R)
        self.assertNotIn(a.rule, {"payment_confirmation", "partial_payment"})

    def test_other_brand_amount_match_never_resolves(self):
        bill = msg("f1", "facturacion@agua-ejemplo.example", "Recibo de marzo",
                   "Tu recibo de marzo por $310.00 vence el 25 de marzo de 2026. Paga hoy.", R)
        pay = msg("p1", "pagos@monedero.example", "Pago recibido",
                  "Gracias por tu pago de $310.00 a agua-ejemplo.", "2026-03-03T15:00:00Z")
        _, links, cases, _ = run([bill, pay])
        self.assertNotIn(cases[links["f1"]]["status"], {"resolved", "closed"})


if __name__ == "__main__":
    unittest.main()
