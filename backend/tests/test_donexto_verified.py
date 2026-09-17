import os
import unittest
from types import SimpleNamespace

from fastapi import HTTPException

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault(
    "OAUTH_ENCRYPTION_KEY",
    "test-oauth-encryption-key-32chars!!",
)

from app.security.donexto_verified import (
    can_mark_donexto_verified,
    read_donexto_verified,
    trusted_donexto_verified,
    user_has_oauth_identity,
)
from app.api.identity import confirm_donexto_identity


class DonextoVerifiedTests(unittest.TestCase):
    def test_confirmation_requires_donexto_verify_query(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            confirm_donexto_identity(
                SimpleNamespace(query_params={})  # type: ignore[arg-type]
            )
        self.assertEqual(caught.exception.status_code, 403)

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

    def test_oauth_identity_cannot_be_marked(self) -> None:
        self.assertFalse(
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

    def test_legacy_oauth_flag_is_not_trusted(self) -> None:
        self.assertFalse(
            trusted_donexto_verified(
                {"donexto_verified": True},
                oauth_identity_present=True,
            )
        )
        self.assertTrue(
            trusted_donexto_verified(
                {
                    "donexto_verified": True,
                    "donexto_verification_source": "email",
                },
                oauth_identity_present=True,
            )
        )

    def test_oauth_account_needs_donexto_email_confirmation(self) -> None:
        self.assertFalse(
            trusted_donexto_verified(
                {"donexto_verified": True},
                oauth_identity_present=True,
            )
        )

    def test_new_oauth_account_without_flag_is_unverified(self) -> None:
        self.assertFalse(
            trusted_donexto_verified({}, oauth_identity_present=True)
        )


if __name__ == "__main__":
    unittest.main()
