import unittest

from app.services.donexto_account_lookup import admin_users_exist, normalize_lookup_email


class DonextoAccountLookupTest(unittest.TestCase):
    def test_normalize_email(self) -> None:
        self.assertEqual(
            normalize_lookup_email("  HS@Yahoo.COM "),
            "hs@yahoo.com",
        )
        self.assertIsNone(normalize_lookup_email("hsalcidor"))
        self.assertIsNone(normalize_lookup_email("sin-dominio@correo"))

    def test_admin_payload_list(self) -> None:
        self.assertTrue(
            admin_users_exist(
                {"users": [{"email": "hsalcidor@yahoo.com"}]},
                "hsalcidor@yahoo.com",
            )
        )
        self.assertFalse(
            admin_users_exist(
                {"users": []},
                "nuevo@yahoo.com",
            )
        )

    def test_admin_payload_single_user(self) -> None:
        self.assertTrue(
            admin_users_exist(
                {"user": {"email": "a@gmail.com"}},
                "a@gmail.com",
            )
        )
        self.assertFalse(
            admin_users_exist(
                {"user": {"email": "b@gmail.com"}},
                "a@gmail.com",
            )
        )
