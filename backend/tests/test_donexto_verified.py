import os
import unittest

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault(
    "OAUTH_ENCRYPTION_KEY",
    "test-oauth-encryption-key-32chars!!",
)

from app.security.donexto_verified import (
    can_mark_donexto_verified,
    read_donexto_verified,
    user_has_oauth_identity,
)


class DonextoVerifiedTests(unittest.TestCase):
    def test_reads_only_app_metadata(self) -> None:
        self.assertFalse(read_donexto_verified({"donexto_verified": False}))
        self.assertTrue(read_donexto_verified({"donexto_verified": True}))
        self.assertFalse(read_donexto_verified(None))

    def test_user_metadata_donexto_verified_is_not_trusted(self) -> None:
        self.assertFalse(
            can_mark_donexto_verified(
                {
                    "user_metadata": {"donexto_verified": True},
                    "app_metadata": {},
                    "identities": [{"provider": "email"}],
                }
            )
        )

    def test_oauth_identity_can_be_marked(self) -> None:
        self.assertTrue(
            can_mark_donexto_verified(
                {
                    "identities": [{"provider": "google"}],
                    "user_metadata": {},
                    "app_metadata": {},
                }
            )
        )
        self.assertTrue(
            user_has_oauth_identity(
                user_metadata={"signup_via": "yahoo_oauth"},
            )
        )

    def test_confirmed_email_can_be_marked(self) -> None:
        self.assertTrue(
            can_mark_donexto_verified(
                {
                    "email_confirmed_at": "2026-09-04T00:00:00Z",
                    "identities": [{"provider": "email"}],
                    "user_metadata": {},
                    "app_metadata": {},
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
