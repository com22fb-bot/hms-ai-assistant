"""Cierre v1 (ASTRA, secciones 7-8): correcciones M35/M36, M04, a), c), d), f) con redacciones nuevas y controles."""
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


class FixTests(unittest.TestCase):
    def test_distinct_lines_same_provider_not_merged(self):
        _, links, cases, _ = run([
            msg("p1", "cobros@telefonia-alfa.example", "Tu recibo", "Cuenta con terminación 1122. Total $350.00. Fecha límite de pago: 28/11/2026.", "2026-11-10T15:00:00Z"),
            msg("p2", "cobros@telefonia-alfa.example", "Tu recibo", "Cuenta con terminación 3344. Total $650.00. Fecha límite de pago: 28/11/2026.", "2026-11-10T15:01:00Z"),
        ])
        self.assertNotEqual(links["p1"], links["p2"])

    def test_same_line_reminder_still_merges(self):
        _, links, _, _ = run([
            msg("r1", "cobros@telefonia-alfa.example", "Tu recibo", "Contrato 556677. Total $350.00. Fecha límite de pago: 28/11/2026.", "2026-11-10T15:00:00Z"),
            msg("r2", "cobros@telefonia-alfa.example", "Recordatorio: tu recibo", "Contrato 556677. Total $350.00. Fecha límite de pago: 28/11/2026.", "2026-11-20T15:00:00Z"),
        ])
        self.assertEqual(links["r1"], links["r2"])

    def test_year_is_not_a_line_id(self):
        from app.services.brain_v1.documents import line_id

        self.assertIsNone(line_id("Estado de cuenta noviembre 2026", ""))

    def test_phishing_urgency_hoy_aqui_goes_to_review(self):
        a = analyze("avisos@notificaciones-web.example", "Netflix: pago rechazado", "Actualiza tus datos aquí hoy o perderás el servicio.")
        self.assertEqual(a.phishing_brand, "netflix")
        self.assertFalse(a.actionable)

    def test_compromised_account_is_n1(self):
        _, links, cases, _ = run([msg("c1", "security@nube-archivos.example", "Your account was compromised",
                                      "We have locked your account. Reset your password immediately.", "2026-10-12T16:00:00Z")])
        self.assertEqual(cases[links["c1"]]["priority"], "critical")

    def test_pagaste_from_bank_is_possible_payment(self):
        _, links, cases, _ = run([
            msg("i1", "recibos@luz-valle.example", "Tu recibo de luz", "Total $520.00. Vence: 30/11/2026.", "2026-11-05T15:00:00Z"),
            msg("i2", "alertas@banco-luna.example", "Operación exitosa", "Pagaste $520.00 a Luz Valle desde tu cuenta.", "2026-11-12T15:00:00Z"),
        ])
        case = cases[links["i1"]]
        self.assertNotEqual(case["status"], "resolved")
        self.assertEqual(case["metadata"].get("payment_status"), "possible")

    def test_quedo_atento_a_outbound_waits(self):
        a = analyze("yo@correo.example", "Cotización 88", "Quedo atenta a tu respuesta antes del martes.", direction="outbound")
        self.assertEqual(a.rule, "outbound_wait")

    def test_copy_in_other_mailbox_after_payment_not_duplicated(self):
        from tests.fake_supabase import FakeSupabase
        from app.services.brain_v1.engine import classify_pending_messages_v1

        inv = "Folio 77123. Total $300.00. Vence: 30/11/2026."
        a1 = msg("g1", "facturas@agua-norte.example", "Tu factura", inv, "2026-11-01T15:00:00Z")
        a2 = msg("g2", "facturas@agua-norte.example", "Gracias por tu pago", "Tu pago de $300.00 del folio #77123 fue acreditado.", "2026-11-08T15:00:00Z")
        b1 = {**msg("g3", "facturas@agua-norte.example", "Tu factura", inv, "2026-11-01T15:00:00Z"), "account_id": "B"}
        db = FakeSupabase({"communication_accounts": [{"id": "A", "workspace_id": "W"}, {"id": "B", "workspace_id": "W"}],
                           "communication_messages": [a1, a2, b1], "intelligent_cases": [], "case_messages": [], "case_events": [],
                           "case_participants": [], "learning_patterns": [], "organizational_patterns": []})
        classify_pending_messages_v1(client=db, account_id="A", workspace_id="W", messages=[a1, a2], user_verified=True)
        classify_pending_messages_v1(client=db, account_id="B", workspace_id="W", messages=[b1], user_verified=True)
        self.assertEqual(len(db.tables["intelligent_cases"]), 1)
        self.assertEqual(db.tables["intelligent_cases"][0]["status"], "resolved")


class ControlTests(unittest.TestCase):
    def test_idempotent_reclassification(self):
        from tests.fake_supabase import FakeSupabase
        from app.services.brain_v1.engine import classify_pending_messages_v1

        m = msg("d1", "facturas@gas-sur.example", "Factura", "Folio 4411. Total $200.00. Vence: 30/11/2026.", "2026-11-01T15:00:00Z")
        db = FakeSupabase({"communication_accounts": [{"id": "A", "workspace_id": "W"}], "communication_messages": [m],
                           "intelligent_cases": [], "case_messages": [], "case_events": [], "case_participants": [],
                           "learning_patterns": [], "organizational_patterns": []})
        for _ in range(2):
            classify_pending_messages_v1(client=db, account_id="A", workspace_id="W", messages=[dict(m)], user_verified=True)
        self.assertEqual(len(db.tables["intelligent_cases"]), 1)
        self.assertEqual(len(db.tables["case_messages"]), 1)

    def test_cancellation_leaves_no_active_appointment(self):
        _, links, cases, _ = run([
            msg("a1", "citas@clinica-rio.example", "Confirmación de cita", "Tu cita es el 20 de noviembre de 2026 a las 10:00.", "2026-11-01T15:00:00Z"),
            msg("a2", "citas@clinica-rio.example", "Cita cancelada", "Tu cita del 20 de noviembre de 2026 fue cancelada.", "2026-11-05T15:00:00Z"),
        ])
        self.assertEqual(cases[links["a1"]]["status"], "no_action")

    def test_signals_carry_version_confidence_and_review_reason(self):
        a = analyze("ana@amigos.example", "hola", "oye, luego vemos lo de aquello")
        s = a.signals()
        self.assertEqual(s["brain_version"], "brain-v1-cierre")
        self.assertIn("confidence", s)
        if a.triage == "review":
            self.assertTrue(s["review_reason"])
        self.assertNotIn("body", s)
        self.assertNotIn("sender", s)

    def test_error_never_hides_mail_nor_closes(self):
        from unittest import mock
        from tests.fake_supabase import FakeSupabase
        from app.services.brain_v1 import engine

        m = msg("e1", "facturas@gas-sur.example", "Factura", "Folio 9. Total $200.00. Vence: 30/11/2026.", "2026-11-01T15:00:00Z")
        db = FakeSupabase({"communication_accounts": [{"id": "A", "workspace_id": "W"}], "communication_messages": [m],
                           "intelligent_cases": [], "case_messages": [], "case_events": [], "case_participants": [],
                           "learning_patterns": [], "organizational_patterns": []})
        with mock.patch.object(engine, "analyze", side_effect=RuntimeError("boom")):
            out = engine.classify_pending_messages_v1(client=db, account_id="A", workspace_id="W", messages=[m], user_verified=True)
        self.assertEqual(out["errors"], 1)
        row = db.tables["communication_messages"][0]
        self.assertEqual(row["triage_category"], "review")
        self.assertFalse([c for c in db.tables["intelligent_cases"] if c.get("status") in {"resolved", "closed"}])


if __name__ == "__main__":
    unittest.main()
