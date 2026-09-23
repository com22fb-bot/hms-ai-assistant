import os
import unittest
from unittest.mock import MagicMock

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault(
    "OAUTH_ENCRYPTION_KEY",
    "test-oauth-encryption-key-32chars!!",
)

from app.security.donexto_verified import (
    merge_trusted_email_verification,
    raw_user_is_trusted_verified,
)
from app.services.donexto_verified_backfill import (
    apply_donexto_verified_backfill,
    is_donexto_verified_backfill_candidate,
)
from app.services.oauth_verification_cleanup import (
    clear_legacy_oauth_verification,
    is_legacy_oauth_verified_user,
)


def _oauth_user(**overrides):
    user = {
        "id": "oauth-hector",
        "email": "hmcelinfo@gmail.com",
        "identities": [{"provider": "google"}],
        "user_metadata": {"donexto_verified": True, "signup_via": "google_oauth"},
        "app_metadata": {"provider": "google"},
    }
    user.update(overrides)
    return user


class DonextoVerifiedBackfillTests(unittest.TestCase):
    def test_historical_oauth_user_metadata_is_a_candidate(self) -> None:
        self.assertTrue(is_donexto_verified_backfill_candidate(_oauth_user()))

    def test_live_check_does_not_trust_that_same_user_metadata(self) -> None:
        self.assertFalse(raw_user_is_trusted_verified(_oauth_user()))

    def test_password_account_with_historical_flag_is_a_candidate(self) -> None:
        user = {
            "id": "email-1",
            "email": "persona@example.com",
            "identities": [{"provider": "email"}],
            "user_metadata": {"donexto_verified": True},
            "app_metadata": {},
        }
        self.assertTrue(is_donexto_verified_backfill_candidate(user))

    def test_metadata_without_a_real_identity_is_not_a_candidate(self) -> None:
        user = {
            "id": "anon-1",
            "email": "persona@example.com",
            "identities": [],
            "user_metadata": {"donexto_verified": True},
            "app_metadata": {},
        }
        self.assertFalse(is_donexto_verified_backfill_candidate(user))

    def test_brand_new_oauth_is_not_a_candidate(self) -> None:
        user = _oauth_user(user_metadata={"signup_via": "google_oauth"})
        self.assertFalse(is_donexto_verified_backfill_candidate(user))

    def test_string_flag_is_not_a_candidate(self) -> None:
        user = _oauth_user(user_metadata={"donexto_verified": "true"})
        self.assertFalse(is_donexto_verified_backfill_candidate(user))

    def test_already_trusted_account_is_skipped(self) -> None:
        user = _oauth_user(
            app_metadata={
                "provider": "google",
                "donexto_verified": True,
                "donexto_verification_source": "email",
            }
        )
        client = MagicMock()
        self.assertFalse(is_donexto_verified_backfill_candidate(user))
        self.assertFalse(apply_donexto_verified_backfill(client, user))
        client.auth.admin.update_user_by_id.assert_not_called()

    def test_apply_writes_email_source_without_dropping_provider(self) -> None:
        user = _oauth_user()
        client = MagicMock()
        self.assertTrue(apply_donexto_verified_backfill(client, user))
        payload = client.auth.admin.update_user_by_id.call_args.args[1]["app_metadata"]
        self.assertEqual(payload["provider"], "google")
        self.assertTrue(payload["donexto_verified"])
        self.assertEqual(payload["donexto_verification_source"], "email")
        self.assertTrue(payload["donexto_verified_at"])

        migrated = _oauth_user(app_metadata=payload)
        self.assertTrue(raw_user_is_trusted_verified(migrated))
        self.assertFalse(is_legacy_oauth_verified_user(migrated))
        self.assertFalse(clear_legacy_oauth_verification(MagicMock(), migrated))

    def test_merge_preserves_existing_timestamp(self) -> None:
        merged = merge_trusted_email_verification(
            {"provider": "email"},
            verified_at="2026-08-01T00:00:00+00:00",
        )
        self.assertEqual(merged["donexto_verified_at"], "2026-08-01T00:00:00+00:00")
        self.assertEqual(merged["donexto_verification_source"], "email")


if __name__ == "__main__":
    unittest.main()
