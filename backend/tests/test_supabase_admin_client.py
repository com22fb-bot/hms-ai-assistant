"""Service-role client must keep admin credentials after verify_otp."""

from __future__ import annotations

import base64
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from supabase import create_client

from app.database.supabase import admin_key_block_reason, get_supabase_client


_URL = "https://example.supabase.co"
_SECRET = "sb_secret_example_not_a_real_key"


def _unsigned_jwt(role: str) -> str:
    def segment(payload: dict[str, str]) -> str:
        raw = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
        return raw.rstrip("=")

    return f"{segment({'alg': 'none'})}.{segment({'role': role})}.sig"


def _settings(secret: str) -> SimpleNamespace:
    return SimpleNamespace(supabase_url=_URL, supabase_secret_key=secret)


class SupabaseAdminClientTests(unittest.TestCase):
    def test_sb_secret_and_service_role_jwt_are_admin_capable(self) -> None:
        self.assertIsNone(admin_key_block_reason(_SECRET))
        self.assertIsNone(admin_key_block_reason(_unsigned_jwt("service_role")))
        self.assertIsNone(admin_key_block_reason("test-secret-key-not-real"))

    def test_publishable_and_anon_jwt_cannot_admin(self) -> None:
        self.assertEqual(
            admin_key_block_reason("sb_publishable_example"),
            "publishable_key",
        )
        self.assertEqual(
            admin_key_block_reason(_unsigned_jwt("anon")),
            "jwt_role_not_service",
        )
        self.assertEqual(
            admin_key_block_reason(_unsigned_jwt("authenticated")),
            "jwt_role_not_service",
        )

    def test_stock_client_replaces_admin_authorization_on_signed_in(self) -> None:
        """supabase-py 2.31 shares auth and admin headers. This is the production bug."""
        client = create_client(_URL, _SECRET)
        self.assertIs(client.auth.admin._headers, client.auth._headers)
        client.auth._notify_all_subscribers(
            "SIGNED_IN",
            SimpleNamespace(access_token="user-access-token"),
        )
        self.assertIn("user-access-token", client.auth.admin._headers["Authorization"])

    def test_service_client_keeps_admin_key_after_signed_in(self) -> None:
        with patch("app.database.supabase.settings", _settings(_SECRET)):
            client = get_supabase_client()

        self.assertIsNot(client.auth.admin._headers, client.auth._headers)
        self.assertFalse(client.auth._auto_refresh_token)
        self.assertFalse(client.auth._persist_session)
        client.auth._notify_all_subscribers(
            "SIGNED_IN",
            SimpleNamespace(access_token="user-access-token"),
        )
        self.assertEqual(
            client.auth.admin._headers["Authorization"],
            f"Bearer {_SECRET}",
        )
        self.assertEqual(client.auth.admin._headers["apiKey"], _SECRET)
        self.assertNotIn("user-access-token", client.auth.admin._headers["Authorization"])
        self.assertIn("user-access-token", client.auth._headers["Authorization"])

    def test_shared_admin_headers_are_restored_after_signed_in(self) -> None:
        with patch("app.database.supabase.settings", _settings(_SECRET)):
            client = get_supabase_client()
        client.auth.admin._headers = client.auth._headers
        client.auth._notify_all_subscribers(
            "SIGNED_IN",
            SimpleNamespace(access_token="user-access-token"),
        )
        self.assertEqual(
            client.auth.admin._headers["Authorization"],
            f"Bearer {_SECRET}",
        )
        self.assertNotIn("user-access-token", client.auth.admin._headers["Authorization"])

    def test_publishable_key_fails_fast_without_leaking_the_key(self) -> None:
        secret = "sb_publishable_example"
        with patch("app.database.supabase.settings", _settings(secret)):
            with self.assertRaises(HTTPException) as caught:
                get_supabase_client()
        self.assertEqual(caught.exception.status_code, 500)
        self.assertEqual(caught.exception.detail.get("reason"), "publishable_key")
        self.assertNotIn(secret, str(caught.exception.detail))
        self.assertIn("sb_secret_", caught.exception.detail.get("message", ""))

    def test_anon_jwt_fails_fast(self) -> None:
        secret = _unsigned_jwt("anon")
        with patch("app.database.supabase.settings", _settings(secret)):
            with self.assertRaises(HTTPException) as caught:
                get_supabase_client()
        self.assertEqual(caught.exception.status_code, 500)
        self.assertEqual(caught.exception.detail.get("reason"), "jwt_role_not_service")
        self.assertNotIn(secret, str(caught.exception.detail))


if __name__ == "__main__":
    unittest.main()
