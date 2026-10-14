import unittest

from app.services import import_categories as ic


class TaxonomyV2PreviewTests(unittest.TestCase):
    def test_catalog_order_and_worlds(self):
        self.assertEqual(
            [(a, w) for a, _, w in ic.V2_AREAS],
            [("trabajo", "ocupacion"), ("hogar", "hogar"), ("dinero", "hogar"), ("compras", "hogar"),
             ("salud", "personal"), ("viajes", "personal"), ("promociones", "personal")],
        )
        self.assertNotIn("seguridad", ic.V2_AREA_IDS)
        self.assertNotIn("other", ic.V2_AREA_IDS)

    def test_every_legacy_category_maps_to_v2_or_review(self):
        for cat in ic.CATEGORY_IDS:
            if cat == "security":
                continue
            self.assertIn(ic.LEGACY_TO_V2[cat], (*ic.V2_AREA_IDS, ic.REVIEW_ID), cat)

    def test_areas(self):
        cases = [
            ("Acme <p@acme.com>", "Propuesta proyecto Q4", "trabajo"),
            ("Escuela <a@escuela.mx>", "Colegiatura octubre", "hogar"),
            ("CFE <avisos@cfe.mx>", "Tu recibo de luz", "dinero"),
            ("SAT <n@sat.gob.mx>", "Aviso SAT", "dinero"),
            ("Amazon <o@amazon.com.mx>", "Tu pedido fue enviado", "compras"),
            ("GNP <p@gnp.com.mx>", "Tu póliza", "salud"),
            ("Volaris <v@volaris.com>", "Tu vuelo", "viajes"),
            ("YouTube <noreply@youtube.com>", "Nuevo video", "promociones"),
            ("Tienda <h@tienda.com>", "50% de descuento", "promociones"),
            ("Ana <ana@ejemplo.mx>", "hola", "revisar"),
        ]
        for sender, subject, area in cases:
            self.assertEqual(ic.v2_area(sender, subject), area, subject)

    def test_security_is_flag_not_area(self):
        self.assertTrue(ic.is_security("Banco <a@banco.mx>", "Alerta de seguridad en tu tarjeta"))
        self.assertEqual(ic.v2_area("Banco <a@banco.mx>", "Alerta de seguridad en tu tarjeta"), "dinero")
        self.assertEqual(ic.v2_area("X <a@x.mx>", "Tu código de verificación"), "revisar")
        s = ic.summarize([("X <a@x.mx>", "Tu código de verificación", []), ("Ana <a@b.mx>", "hola", [])])
        self.assertEqual(s["security"], 1)
        self.assertEqual(s["review"], 2)
        self.assertEqual(sum(s["worlds"].values()), 0)
        self.assertEqual(s["taxonomy"], "v2")

    def test_protected_kept_even_if_area_excluded(self):
        excl = ["dinero", "promociones"]
        self.assertFalse(ic.skip_message(excl, "CFE <a@cfe.mx>", "Tu recibo de luz"))  # facturas protegida
        self.assertFalse(ic.skip_message(excl, "Banco <a@banco.mx>", "Transferencia SPEI"))  # bancos
        self.assertFalse(ic.skip_message(excl, "Instagram <s@mail.instagram.com>", "Alerta de seguridad"))
        self.assertTrue(ic.skip_message(excl, "Tienda <h@tienda.com>", "50% de descuento"))
        # Si el usuario apaga la protección, sí se salta.
        self.assertTrue(ic.skip_message([*excl, "proteger:facturas"], "CFE <a@cfe.mx>", "Tu recibo de luz"))

    def test_clean_exclude_accepts_v2_and_legacy(self):
        self.assertEqual(
            ic.clean_exclude(["promociones", "revisar", "proteger:salud", "promos", "otros", "x"]),
            ["promociones", "promos", "proteger:salud", "revisar"],
        )

    def test_gmail_query_never_drops_protected_server_side(self):
        self.assertEqual(ic.gmail_query_exclusions(["promociones"]), "")
        all_off = ["promociones", *(ic.PROTECTED_PREFIX + p for p in ic.PROTECTED_IDS)]
        self.assertIn("-category:promotions", ic.gmail_query_exclusions(all_off))


if __name__ == "__main__":
    unittest.main()
