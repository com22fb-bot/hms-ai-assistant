"""Taxonomía v2 + detector de phishing para marcas desconocidas (ASTRA, 14-oct-2026).

Redacción propia y general: ningún texto del corpus L6 se copia aquí.
"""
from __future__ import annotations

import unittest

from app.services.brain_v1.taxonomy_v2 import AREAS, CATALOG
from tests.test_brain_v1_etapa12 import analyze, msg, run

R = "2026-05-04T15:00:00Z"


class AreasV2Tests(unittest.TestCase):
    def test_only_seven_areas_and_closed_tags(self):
        self.assertEqual(len(AREAS), 7)
        for s, sub, body in (
            ("rh@empresa-uno.example", "Tu recibo de nómina", "Adjuntamos tu recibo de nómina de la quincena."),
            ("tienda@zapatos.example", "Pedido ZP-88231 confirmado", "Gracias por tu compra, tu pedido ZP-88231 fue confirmado."),
            ("x@foro.example", "Boletín mensual", "Las noticias del mes."),
        ):
            a = analyze(s, sub, body, R)
            self.assertIn(a.area, AREAS)
            self.assertTrue(set(a.area_tags) <= set(CATALOG[a.area]), a.area_tags)

    def test_work_vs_personal(self):
        self.assertEqual(analyze("rh@empresa-uno.example", "Recibo de nómina", "Adjuntamos tu recibo de nómina de octubre.", R).area, "trabajo")
        self.assertEqual(analyze("avisos@banco-sur.example", "Depósito recibido", "Recibiste un depósito de nómina por $9,000.00 MXN.", R).area, "dinero")
        inv = analyze("cxp@consultores-beta.example", "Factura FB-7781", "Estimados, les compartimos la factura FB-7781 por $40,000.00 MXN por servicios de consultoría. Fecha límite de pago: 2026-06-10.", R)
        self.assertEqual(inv.area, "trabajo")
        self.assertIn("Proveedores", inv.area_tags)
        self.assertEqual(analyze("pmo@empresa-uno.example", "Reunión de seguimiento del proyecto Sol", "Revisemos avances del proyecto Sol el 2026-06-02 a las 9:00.", R).area, "trabajo")

    def test_agenda_is_remapped_by_topic(self):
        self.assertEqual(analyze("citas@clinica-norte.example", "Cita médica", "Tu cita con el Dr. Paz quedó para el 2026-06-03 a las 10:00.", R).area, "salud")
        self.assertEqual(analyze("avisos@colegio-luz.example", "Junta de padres de familia", "La junta será el 2026-06-05 a las 18:00.", R).area, "hogar")
        self.assertEqual(analyze("boletos@arena-sur.example", "Tus boletos", "Tus boletos para el concierto del 2026-07-01.", R).area, "viajes")

    def test_security_is_flag_with_topic_area(self):
        a = analyze("alertas@banco-sur.example", "Cargo no reconocido", "Detectamos un cargo de $800.00 en tu tarjeta. Si no lo reconoces, bloquéala desde la app oficial.", R)
        self.assertEqual(a.area, "dinero")
        self.assertEqual(a.security_flag, "N1")

    def test_personal_without_topic_is_por_revisar_not_other(self):
        a = analyze("pepe12@correo.example", "Hola", "¿Cómo vas? Hablamos luego.", R)
        self.assertIsNone(a.area)
        self.assertNotEqual(a.signals()["area"], "other")


class PhishingUnknownBrandTests(unittest.TestCase):
    CASES = (
        ("seguridad@banco-rio-verifica.example", "Tu cuenta será suspendida", "Entra a http://banco-rio-verifica.example/login y confirma tu usuario, contraseña y NIP hoy."),
        ("soporte@envios-rapidos.co.example", "Paquete retenido", "Para liberar tu envío paga $29.00 de aduana en http://aduana-pago.example/pago ."),
        ("ceo@miempresa-mail.example", "Pago urgente", "Necesito que hoy hagas una transferencia de $90,000.00 a esta nueva cuenta. Es confidencial."),
        ("info@rendimientos-ya.example", "Duplica tu dinero", "Invierte en cripto desde $300 con ganancias garantizadas. Deposita a la cuenta indicada."),
        ("premios@ganadores-hoy.example", "¡Ganaste!", "Felicidades, ganaste un premio. Reclama tu premio respondiendo con tus datos."),
    )

    def test_detected_as_por_revisar_with_flag(self):
        for s, sub, body in self.CASES:
            a = analyze(s, sub, body, R)
            self.assertEqual(a.rule, "phishing_suspect", body)
            self.assertIsNone(a.area, body)
            self.assertEqual(a.security_flag, "N1", body)
            self.assertIsNone(a.dates.due_at)

    def test_legit_alerts_are_not_phishing(self):
        for s, sub, body in (
            ("codigos@banco-sur.example", "Tu código", "Tu código es 551234. No lo compartas con nadie."),
            ("security@nube-uno.example", "Nuevo inicio de sesión", "Se inició sesión desde un dispositivo nuevo. Si no fuiste tú, cambia tu contraseña desde el sitio oficial."),
            ("ofertas@tienda-azul.example", "Rebajas", "30% de descuento en toda la tienda."),
        ):
            self.assertNotEqual(analyze(s, sub, body, R).rule, "phishing_suspect", body)


class CaseMergeTests(unittest.TestCase):
    def test_identical_subject_distinct_mails_do_not_merge(self):
        body = "Detectamos un cargo de ${} en tu tarjeta. Si no lo reconoces, bloquéala desde la app oficial."
        msgs = [msg(f"m{n}", "alertas@banco-sur.example", "Cargo no reconocido", body.format(f"{n}00.00"), R) for n in (1, 2, 3)]
        for n, m in enumerate(msgs):
            m["thread_id"] = f"t{n}"
        _, links, _, _ = run(msgs)
        self.assertEqual(len({links.get(f"m{n}") for n in (1, 2, 3)} - {None}), len([n for n in (1, 2, 3) if links.get(f"m{n}")]))

    def test_exact_duplicate_is_marked(self):
        a = msg("d1", "maria@correo.example", "Fotos", "Te mando las fotos de la fiesta de ayer.", R)
        b = msg("d2", "maria@correo.example", "Fwd: Fotos", "Te mando las fotos de la fiesta de ayer.\n\nEnviado desde mi iPhone", "2026-05-04T16:00:00Z")
        a["thread_id"], b["thread_id"] = "ta", "tb"
        db, _, _, _ = run([a, b])
        rows = {m["id"]: m for m in db.tables["communication_messages"]}
        self.assertEqual(rows["d2"]["brain_signals"]["duplicate_of"], "d1")


if __name__ == "__main__":
    unittest.main()
