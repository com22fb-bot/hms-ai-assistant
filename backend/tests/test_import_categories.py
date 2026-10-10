import os
import unittest

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault("OAUTH_ENCRYPTION_KEY", "test-oauth-encryption-key-32chars!!")

from app.services import import_categories as ic


class ImportCategoryTests(unittest.TestCase):
    def test_social_by_domain(self):
        self.assertEqual(ic.import_category("YouTube <noreply@youtube.com>", "Nuevo video"), "social")
        self.assertEqual(ic.import_category("Instagram <security@mail.instagram.com>", "Hola"), "social")
        self.assertEqual(ic.social_platform("LinkedIn <messages-noreply@linkedin.com>"), "LinkedIn")

    def test_areas_and_promos(self):
        self.assertEqual(ic.import_category("CFE <avisos@cfe.mx>", "Tu recibo de luz"), "bills")
        self.assertEqual(ic.import_category("Tienda <hola@tienda.com>", "50% de descuento hoy"), "promos")
        self.assertEqual(ic.import_category("Amigo <a@b.com>", "hola"), "other")

    def test_skip(self):
        self.assertTrue(ic.skip_message(["social"], "TikTok <no-reply@tiktok.com>", "x"))
        self.assertFalse(ic.skip_message([], "TikTok <no-reply@tiktok.com>", "x"))
        self.assertEqual(ic.clean_exclude(["social", "hack", "promos"]), ["promos", "social"])

    def test_gmail_query(self):
        q = ic.gmail_query_exclusions(["social", "promos"])
        self.assertIn("-category:promotions", q)
        self.assertIn("youtube.com", q)

    def test_summary(self):
        s = ic.summarize([("a@youtube.com", "v", []), ("x@cfe.mx", "recibo", []), ("p@acme.com", "proyecto Q4", [])])
        self.assertEqual(s["categories"]["social"], 1)
        self.assertEqual(s["spheres"], {"hogar": 1, "ocupacion": 1, "personal": 0})
        self.assertEqual(s["social_platforms"], {"YouTube": 1})


if __name__ == "__main__":
    unittest.main()
