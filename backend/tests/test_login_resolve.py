import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault(
    "OAUTH_ENCRYPTION_KEY",
    "test-oauth-encryption-key-32chars!!",
)

from fastapi import HTTPException

from app.api.login_resolve import (
    LoginResolveRequest,
    resolve_login,
    resolve_mailbox_provider,
)
from app.middleware.authentication_context import AuthenticationContextMiddleware


class _FakeRequest:
    def __init__(self, path: str) -> None:
        self.method = "POST"
        self.url = type("U", (), {"path": path})()
        self.client = type("C", (), {"host": "127.0.0.1"})()
        self.headers = {}


class LoginResolveTests(unittest.TestCase):
    def test_resolve_is_public(self) -> None:
        request = _FakeRequest("/auth/login/resolve")
        self.assertFalse(
            AuthenticationContextMiddleware._requires_identity(request)
        )

    def test_provider_from_domain(self) -> None:
        self.assertEqual(resolve_mailbox_provider("a@gmail.com"), "gmail")
        self.assertEqual(
            resolve_mailbox_provider("hsalcidor@yahoo.com"), "yahoo"
        )
        self.assertEqual(resolve_mailbox_provider("x@outlook.com"), "hotmail")
        self.assertEqual(resolve_mailbox_provider("x@empresa.mx"), "other")

    def test_existing_yahoo_goes_to_oauth(self) -> None:
        with patch(
            "app.api.login_resolve.auth_user_exists", return_value=True
        ):
            result = resolve_login(
                LoginResolveRequest(email="hsalcidor@yahoo.com")
            )
        self.assertTrue(result["exists"])
        self.assertEqual(result["next"], "yahoo_oauth")

    def test_unknown_yahoo_goes_to_signup_not_oauth(self) -> None:
        with patch(
            "app.api.login_resolve.auth_user_exists", return_value=False
        ):
            result = resolve_login(
                LoginResolveRequest(email="melgibson@yahoo.com")
            )
        self.assertFalse(result["exists"])
        self.assertEqual(result["next"], "signup")
        self.assertEqual(result["provider"], "yahoo")

    def test_unknown_email_goes_to_signup(self) -> None:
        with patch(
            "app.api.login_resolve.auth_user_exists", return_value=False
        ):
            result = resolve_login(
                LoginResolveRequest(email="nuevo@gmail.com")
            )
        self.assertFalse(result["exists"])
        self.assertEqual(result["next"], "signup")

    def test_rejects_bad_email(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            resolve_login(LoginResolveRequest(email="not-an-email"))
        self.assertEqual(caught.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
