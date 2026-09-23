import os
import unittest
from unittest.mock import MagicMock

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault(
    "OAUTH_ENCRYPTION_KEY",
    "test-oauth-encryption-key-32chars!!",
)

from app.services.oauth_verification_cleanup import (
    clear_legacy_oauth_verification,
    is_legacy_oauth_verified_user,
)


class OAuthVerificationCleanupTests(unittest.TestCase):
    def test_identifies_contaminated_oauth_user(self) -> None:
        user = {
            "id": "oauth-1",
            "identities": [{"provider": "google"}],
            "user_metadata": {},
            "app_metadata": {
                "donexto_verified": True,
                "donexto_verified_at": "2026-09-01T00:00:00Z",
            },
        }
        self.assertTrue(is_legacy_oauth_verified_user(user))

    def test_does_not_touch_email_only_verified_user(self) -> None:
        user = {
            "id": "email-1",
            "identities": [{"provider": "email"}],
            "user_metadata": {},
            "app_metadata": {"donexto_verified": True},
        }
        client = MagicMock()
        self.assertFalse(clear_legacy_oauth_verification(client, user))
        client.auth.admin.update_user_by_id.assert_not_called()

    def test_preserves_oauth_user_verified_by_email_source(self) -> None:
        user = {
            "id": "oauth-2",
            "identities": [{"provider": "google"}],
            "user_metadata": {"donexto_verified": True},
            "app_metadata": {
                "provider": "google",
                "donexto_verified": True,
                "donexto_verification_source": "email",
            },
        }
        client = MagicMock()
        self.assertFalse(is_legacy_oauth_verified_user(user))
        self.assertFalse(clear_legacy_oauth_verification(client, user))
        client.auth.admin.update_user_by_id.assert_not_called()

    def test_clears_only_legacy_fields(self) -> None:
        user = {
            "id": "oauth-3",
            "identities": [{"provider": "yahoo"}],
            "user_metadata": {},
            "app_metadata": {
                "donexto_verified": True,
                "donexto_verified_at": "2026-09-01T00:00:00Z",
                "provider": "custom",
            },
        }
        client = MagicMock()
        self.assertTrue(clear_legacy_oauth_verification(client, user))
        client.auth.admin.update_user_by_id.assert_called_once_with(
            "oauth-3",
            {"app_metadata": {"provider": "custom"}},
        )


if __name__ == "__main__":
    unittest.main()
