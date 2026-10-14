"""Políticas post lote 4 (dictamen ASTRA). Redacción general: ningún texto del lote 4 sellado se copia aquí.

El lote 4 solo se usa fuera del repositorio como regresión conocida (no validante).
"""
from __future__ import annotations

import unittest

from tests.test_brain_v1_etapa12 import analyze, msg, run

R = "2026-05-04T15:00:00Z"


class RiskSignalTests(unittest.TestCase):
    def test_password_modified_plus_not_you_is_case_even_from_noreply(self):
        a = analyze("no-reply@nube-azul.example", "Aviso de cuenta",
                    "La contraseña de tu perfil ha sido cambiada. Si no hiciste este cambio, llama a atención a clientes.", R)
        self.assertEqual((a.rule, a.actionable), ("security_action", True))
        self.assertNotIn(a.triage, {"informational", "notice"})

    def test_password_modified_without_not_you_stays_protected_notice(self):
        a = analyze("no-reply@nube-azul.example", "Aviso de cuenta", "La contraseña de tu perfil ha sido cambiada.", R)
        self.assertEqual(a.protected, "security")
        self.assertFalse(a.actionable)

    def test_compromise_and_fraud_are_high_not_critical(self):
        for sender, subject, body in (
            ("avisos@portal-seguro.example", "Revisión de cuenta", "Creemos que tu cuenta puede estar comprometida. Revisa tus sesiones."),
            ("alertas@credito-sur.example", "Movimiento a revisar", "Registramos una transacción sospechosa de $1,200.00 en tu tarjeta. Revísala en la app."),
        ):
            a = analyze(sender, subject, body, R)
            self.assertEqual(a.rule, "security_action", body)
            _, links, cases, _ = run([msg("r", sender, subject, body, R)])
            self.assertEqual(cases[links["r"]]["priority"], "high")

    def test_negated_share_advice_is_not_credential_request(self):
        a = analyze("avisos@portal-seguro.example", "Revisión de cuenta",
                    "Tu cuenta puede estar comprometida. Nunca compartas tu contraseña con nadie.", R)
        self.assertEqual(a.rule, "security_action")

    def test_link_asking_for_password_or_code_is_phishing_review(self):
        a = analyze("soporte@servicio-x.example", "Mantén tu perfil activo",
                    "Da clic en el botón y escribe tu contraseña y el código que te enviamos por SMS.", R)
        self.assertEqual((a.rule, a.triage, a.actionable), ("phishing_suspect", "review", False))
        self.assertEqual(a.protected, "security")

    def test_code_message_without_link_is_not_phishing(self):
        a = analyze("no-reply@servicio-x.example", "Tu código", "Tu código de acceso es 482913. Escribe este código en la app.", R)
        self.assertNotEqual(a.rule, "phishing_suspect")


class BillTests(unittest.TestCase):
    def test_paid_bill_or_zero_balance_never_opens_case(self):
        for body in ("Tu factura FX-31 de abril ya está pagada.", "Factura FX-32. Saldo actual: $0.00 MXN."):
            a = analyze("cobros@luz-ejemplo.example", "Tu factura", body, R)
            self.assertEqual((a.rule, a.actionable), ("bill_settled", False), body)
            _, links, cases, _ = run([msg("p", "cobros@luz-ejemplo.example", "Tu factura", body, R)])
            self.assertEqual(cases, {})

    def test_total_label_is_not_a_demand_and_no_date_is_invented(self):
        body = "Recibo del servicio 31201, periodo abril. Total a pagar $410.00 MXN."
        a = analyze("facturacion@agua-ejemplo.example", "Tu recibo de abril", body, R)
        self.assertEqual(a.rule, "bill_followup")
        _, links, cases, _ = run([msg("b", "facturacion@agua-ejemplo.example", "Tu recibo de abril", body, R)])
        case = cases[links["b"]]
        self.assertEqual(case["status"], "needs_review")
        self.assertIsNone(case.get("due_at"))

    def test_overdue_date_does_not_raise_priority_by_itself(self):
        body = "Factura 7731 por $300.00 MXN. La fecha límite de pago fue el 1 de mayo de 2026."
        _, links, cases, _ = run([msg("o", "cobros@papeleria.example", "Factura 7731", body, R)])
        case = cases[links["o"]]
        self.assertEqual(case["priority"], "normal")
        self.assertTrue(case["metadata"]["overdue"])

    def test_deadline_within_three_days_is_still_high(self):
        body = "Factura 7732 por $300.00 MXN. Fecha límite de pago 2026-05-06."
        _, links, cases, _ = run([msg("o", "cobros@papeleria.example", "Factura 7732", body, R)])
        self.assertEqual(cases[links["o"]]["priority"], "high")


class PaymentLinkTests(unittest.TestCase):
    def test_payment_by_service_reference_links_without_closing_followup(self):
        bill = msg("f", "facturacion@cable-uno.example", "Recibo abril servicio 40917", "Recibo del servicio 40917 por $650.00 MXN, periodo abril 2026.", "2026-05-01T15:00:00Z")
        pay = msg("p", "cobranza@cable-uno.example", "Pago acreditado", "Confirmamos tu pago de $650.00 MXN del servicio 40917.", "2026-05-03T15:00:00Z")
        _, links, cases, _ = run([bill, pay])
        self.assertEqual(links["p"], links["f"])
        case = cases[links["f"]]
        self.assertNotIn(case["status"], {"resolved", "closed"})
        self.assertEqual(case["metadata"]["payment_status"], "possible")

    def test_partial_payment_updates_but_never_closes(self):
        bill = msg("f", "facturacion@licencias.example", "Factura anual", "Factura anual de licencias por $8,000.00 MXN.", "2026-05-01T15:00:00Z")
        pay = msg("p", "cobros@licencias.example", "Abono recibido", "Recibimos un pago parcial de $2,000.00 MXN. Saldo restante $6,000.00 MXN.", "2026-05-02T15:00:00Z")
        _, links, cases, _ = run([bill, pay])
        self.assertEqual(links["p"], links["f"])
        case = cases[links["f"]]
        self.assertNotIn(case["status"], {"resolved", "closed"})
        self.assertEqual(case["metadata"]["payment_status"], "partial")

    def test_payment_without_reference_goes_to_review(self):
        pay = msg("p", "pagos@desconocido.example", "Pago acreditado", "Confirmamos un pago de $410.00 MXN, sin número de factura.", R)
        _, links, cases, msgs = run([pay])
        self.assertNotIn("p", links)
        self.assertEqual(msgs["p"]["triage_category"], "review")

    def test_payment_never_closes_other_issuers_bill(self):
        bill = msg("f", "cobros@papeleria.example", "Factura 5510", "Factura 5510 por $410.00 MXN. Fecha límite de pago 2026-05-20.", "2026-05-01T15:00:00Z")
        pay = msg("p", "pagos@otra-marca.example", "Pago acreditado", "Confirmamos un pago de $410.00 MXN.", "2026-05-02T15:00:00Z")
        _, links, cases, msgs = run([bill, pay])
        self.assertNotEqual(links.get("p"), links["f"])
        self.assertEqual(cases[links["f"]]["status"], "new")
        self.assertEqual(msgs["p"]["triage_category"], "review")


class BookingTests(unittest.TestCase):
    def test_event_date_comes_from_body_not_received_date(self):
        body = "Tu mesa está reservada para el 2026-06-12 a las 21:00. Código M771."
        a = analyze("reservas-centro@restaurante-luna.example", "Reserva confirmada", body, R)
        self.assertEqual(a.rule, "booking")
        self.assertTrue(a.dates.event_at.startswith("2026-06-12T21:00"))

    def test_stay_range_starts_on_first_day(self):
        a = analyze("hotel@playa-sol.example", "Confirmación de hospedaje", "Tu reservación K22 está confirmada del 2026-07-03 al 2026-07-07.", R)
        self.assertTrue(a.dates.event_at.startswith("2026-07-03"))

    def test_quote_and_waitlist_are_notices(self):
        for body in ("Te compartimos una cotización de viaje a Mérida; la reservación no está confirmada.",
                     "Quedaste en lista de espera para la habitación doble."):
            a = analyze("ventas@agencia-mar.example", "Tu solicitud", body, R)
            self.assertEqual((a.rule, a.triage, a.actionable), ("booking_pending", "notice", False), body)

    def test_cancellation_updates_same_day_booking_only(self):
        conf = msg("c", "boletos@foro-norte.example", "Boletos confirmados", "Tus boletos están confirmados para el concierto del 2026-08-09 a las 20:00.", "2026-05-01T15:00:00Z")
        other = msg("o", "boletos@foro-norte.example", "Boletos confirmados", "Tus boletos están confirmados para el concierto del 2026-09-01 a las 20:00.", "2026-05-01T16:00:00Z")
        cancel = msg("x", "boletos@foro-norte.example", "Evento cancelado", "El evento del 2026-08-09 fue cancelado; se reembolsarán tus boletos.", "2026-05-02T15:00:00Z")
        _, links, cases, _ = run([conf, other, cancel])
        self.assertEqual(links["x"], links["c"])
        self.assertEqual(cases[links["c"]]["status"], "no_action")
        self.assertEqual(cases[links["o"]]["status"], "scheduled")

    def test_two_bookings_same_domain_same_day_stay_separate(self):
        a = msg("a", "vuelos@viajes-unidos.example", "Vuelo confirmado", "Tu vuelo ZX10 está confirmado para el 2026-09-20 a las 07:00.", R)
        b = msg("b", "hoteles@viajes-unidos.example", "Confirmación de hospedaje", "Tu reservación HT9 está confirmada del 2026-09-20 al 2026-09-22.", R)
        _, links, _, _ = run([a, b])
        self.assertNotEqual(links["a"], links["b"])


class RenewalTests(unittest.TestCase):
    def test_upcoming_renewal_with_date_and_amount_is_case_with_due(self):
        body = "Tu membresía se renovará el 2026-06-01 por $149.00 MXN."
        a = analyze("cuentas@gimnasio-red.example", "Próxima renovación", body, R)
        self.assertEqual(a.rule, "renewal_upcoming")
        self.assertTrue(a.dates.due_at.startswith("2026-06-01"))

    def test_upcoming_renewal_without_amount_stays_notice(self):
        a = analyze("cuentas@gimnasio-red.example", "Próxima renovación", "Tu membresía se renovará automáticamente el 2026-06-01.", R)
        self.assertEqual((a.triage, a.actionable), ("notice", False))

    def test_completed_renewal_is_notice(self):
        a = analyze("cuentas@gimnasio-red.example", "Membresía renovada", "Tu membresía fue renovada con éxito.", R)
        self.assertIn(a.rule, {"renewal_done", "auto_notice"})
        self.assertEqual((a.triage, a.actionable), ("notice", False))
        b = analyze("marta.ventas@gimnasio-red.example", "Membresía renovada", "Tu membresía fue renovada con éxito.", R)
        self.assertEqual((b.rule, b.triage), ("renewal_done", "notice"))

    def test_billing_data_or_trial_end_is_case_without_date(self):
        for body in ("Para seguir usando el servicio actualiza tu método de pago.", "Tu prueba gratuita terminó; elige un plan para continuar."):
            a = analyze("cuentas@app-notas.example", "Tu cuenta", body, R)
            self.assertEqual((a.rule, a.actionable), ("renewal_action", True), body)
            self.assertIsNone(a.dates.due_at)


class LessAmbiguousTests(unittest.TestCase):
    def test_order_and_purchase_notices(self):
        for subject, body in (("Tu paquete", "Tu paquete fue entregado en recepción."),
                              ("Gracias", "Confirmación de compra: orden 5521 por $230.00 MXN.")):
            a = analyze("marta.ventas@tienda-azul.example", subject, body, R)
            self.assertEqual((a.rule, a.triage), ("order_notice", "notice"), body)

    def test_requested_stock_alert_is_notice(self):
        a = analyze("alertas@libreria.example", "Ya llegó", "El libro que solicitaste ya está disponible.", R)
        self.assertEqual((a.rule, a.triage), ("stock_alert", "notice"))

    def test_direct_question_from_person_is_request(self):
        for body in ("¿Podrías revisar la propuesta y darme tu opinión?", "¿Comemos el sábado? Avísame si puedes."):
            a = analyze("lucia@correo-personal.example", "Hola", body, R)
            self.assertEqual(a.rule, "request", body)

    def test_ambiguous_rule_still_exists(self):
        a = analyze("ana@amigos.example", "hola", "oye, luego vemos lo de aquello", R)
        self.assertEqual(a.rule, "ambiguous")


class TaxonomyV1Tests(unittest.TestCase):
    """Taxonomía v1 aprobada (13-oct-2026): un área principal + etiquetas secundarias."""

    def test_security_and_bills_areas(self):
        self.assertEqual(analyze("no-reply@nube-azul.example", "Aviso", "Tu cuenta puede estar comprometida.", R).area, "security")
        self.assertEqual(analyze("cobros@papeleria.example", "Factura 9", "Factura 9 por $10.00 MXN. Fecha límite de pago 2026-05-20.", R).area, "bills")

    def test_events_separate_from_travel(self):
        ev = analyze("boletos@foro-norte.example", "Boletos confirmados", "Tus boletos están confirmados para el concierto del 2026-08-09 a las 20:00.", R)
        fl = analyze("vuelos@viajes-unidos.example", "Vuelo confirmado", "Tu vuelo ZX10 está confirmado para el 2026-09-20 a las 07:00.", R)
        self.assertEqual((ev.area, fl.area), ("agenda", "travel"))

    def test_social_and_promos(self):
        self.assertEqual(analyze("x@facebookmail.com", "Nuevo comentario", "Alguien comentó tu foto.", R).area, "social")
        self.assertEqual(analyze("ofertas@tienda-azul.example", "Ofertas", "Descuentos de la semana en toda la tienda.", R).area, "promos")

    def test_insurance_is_secondary_tag_on_bill(self):
        a = analyze("cobros@aseguradora-uno.example", "Factura póliza 77", "Factura de póliza 77 por $900.00 MXN. Fecha límite de pago 2026-05-20.", R)
        self.assertEqual(a.area, "bills")
        self.assertIn("insurance", a.area_tags)

    def test_signals_carry_area(self):
        s = analyze("ana@amigos.example", "hola", "oye, luego vemos lo de aquello", R).signals()
        self.assertIn("area", s)
        self.assertEqual(s["area"], "other")  # baja confianza analizada = Otros (distinto de pendiente)
