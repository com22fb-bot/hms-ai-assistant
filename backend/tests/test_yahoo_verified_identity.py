import os
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault(
    "OAUTH_ENCRYPTION_KEY",
    "test-oauth-encryption-key-32chars!!",
)

from app.services.yahoo_session import _ensure_yahoo_auth_user


class YahooVerifiedIdentityTests(unittest.TestCase):
    def test_existing_yahoo_user_is_marked_verified(self) -> None:
        admin = MagicMock()
        client = MagicMock()
        client.auth.admin = admin
        existing = {
            "id": "user-1",
            "email": "hsalcidor@yahoo.com",
            "user_metadata": {"donexto_verified": False, "full_name": "Héctor"},
        }
        with patch(
            "app.services.yahoo_session._find_user_by_email",
            return_value=existing,
        ):
            user_id, password = _ensure_yahoo_auth_user(
                client, "hsalcidor@yahoo.com"
            )
        self.assertEqual(user_id, "user-1")
        self.assertIsNone(password)
        payload = admin.update_user_by_id.call_args.args[1]
        self.assertTrue(payload["app_metadata"]["donexto_verified"])
        self.assertEqual(payload["user_metadata"]["signup_via"], "yahoo_oauth")
        self.assertEqual(payload["user_metadata"]["full_name"], "Héctor")

    def test_new_yahoo_user_is_created_verified(self) -> None:
        admin = MagicMock()
        created = MagicMock()
        created.user = {
            "id": "user-2",
            "email": "nuevo@yahoo.com",
            "user_metadata": {},
        }
        admin.create_user.return_value = created
        client = MagicMock()
        client.auth.admin = admin
        with patch(
            "app.services.yahoo_session._find_user_by_email",
            return_value={},
        ):
            user_id, password = _ensure_yahoo_auth_user(
                client, "nuevo@yahoo.com", allow_create=True
            )
        self.assertEqual(user_id, "user-2")
        self.assertTrue(password)
        created_payload = admin.create_user.call_args.args[0]
        self.assertTrue(created_payload["app_metadata"]["donexto_verified"])
