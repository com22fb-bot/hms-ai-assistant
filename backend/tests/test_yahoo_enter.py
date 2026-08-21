import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault(
    "OAUTH_ENCRYPTION_KEY",
    "test-oauth-encryption-key-32chars!!",
)

from fastapi import HTTPException

from app.api.yahoo_mail import YahooConnectRequest, yahoo_connect, yahoo_enter
from app.middleware.authentication_context import AuthenticationContextMiddleware
from app.services.yahoo_oauth import (
    build_yahoo_authorization_url,
    granted_mail_read,
    sanitize_return_to,
)


class _FakeRequest:
    def __init__(self, path: str, method: str = "POST") -> None:
        self.method = method
        self.url = SimpleNamespace(path=path)
        self.client = SimpleNamespace(host="127.0.0.1")
        self.headers = {}


class YahooOAuthGateTests(unittest.TestCase):
    def test_login_and_callback_are_public(self) -> None:
        login = _FakeRequest("/auth/yahoo/login")
        callback = _FakeRequest("/auth/yahoo/callback", method="GET")
        self.assertFalse(
            AuthenticationContextMiddleware._requires_identity(login)
        )
        self.assertFalse(
            AuthenticationContextMiddleware._requires_identity(callback)
        )
        connect = _FakeRequest("/auth/yahoo/connect")
        self.assertTrue(
            AuthenticationContextMiddleware._requires_identity(connect)
        )

    def test_enter_rejects_yahoo_password(self) -> None:
        payload = YahooConnectRequest(
            email="hsalcidor@yahoo.com",
            app_password="clave-yahoo-1",
        )
        with self.assertRaises(HTTPException) as caught:
            yahoo_enter(payload, _FakeRequest("/auth/yahoo/enter"))  # type: ignore[arg-type]
        self.assertEqual(caught.exception.status_code, 410)
        detail = caught.exception.detail
        self.assertIn("no pide la contraseña", str(detail).lower())

    def test_connect_rejects_yahoo_password(self) -> None:
        payload = YahooConnectRequest(
            email="hsalcidor@yahoo.com",
            app_password="clave-yahoo-1",
        )
        with self.assertRaises(HTTPException) as caught:
            yahoo_connect(payload)
        self.assertEqual(caught.exception.status_code, 410)

    def test_authorization_url_points_to_yahoo(self) -> None:
        with patch(
            "app.services.yahoo_oauth.settings"
        ) as settings:
            settings.yahoo_client_id = "client-id"
            settings.yahoo_client_secret = "secret"
            settings.yahoo_redirect_uri = (
                "https://hms-ai-assistant-production.up.railway.app"
                "/auth/yahoo/callback"
            )
            settings.yahoo_oauth_scopes = "openid email profile"
            url = build_yahoo_authorization_url("state-token")
        self.assertIn("https://api.login.yahoo.com/oauth2/request_auth", url)
        self.assertIn("client_id=client-id", url)
        self.assertIn("state=state-token", url)
        self.assertIn("openid", url)
        self.assertIn("prompt=login", url)
        self.assertNotIn("mail-r", url)

    def test_sanitize_return_to_stays_on_donexto(self) -> None:
        with patch(
            "app.services.yahoo_oauth.settings"
        ) as settings:
            settings.frontend_origins = ["https://app.donexto.com"]
            self.assertEqual(
                sanitize_return_to("https://evil.example/phish"),
                "https://app.donexto.com/",
            )
            self.assertEqual(
                sanitize_return_to("https://app.donexto.com/admin"),
                "https://app.donexto.com/",
            )

    def test_login_requires_yahoo_app(self) -> None:
        from app.api.yahoo_mail import yahoo_login

        with patch("app.services.yahoo_oauth.settings") as settings:
            settings.yahoo_client_id = ""
            settings.yahoo_client_secret = ""
            settings.yahoo_redirect_uri = ""
            with self.assertRaises(HTTPException) as caught:
                yahoo_login(_FakeRequest("/auth/yahoo/login"), None)
        self.assertEqual(caught.exception.status_code, 503)
        self.assertIn("yahoo_oauth_not_configured", str(caught.exception.detail))

    def test_mail_read_scope_detection(self) -> None:
        self.assertTrue(granted_mail_read({"scope": "openid email mail-r"}))
        self.assertTrue(granted_mail_read({"scope": "openid,mail-w"}))
        self.assertFalse(granted_mail_read({"scope": "openid email profile"}))

    def test_invalid_scope_message_is_spanish(self) -> None:
        from app.api.yahoo_mail import _yahoo_callback_error_message

        text = _yahoo_callback_error_message("invalid_scope", "invalid scope")
        self.assertIn("identidad", text.lower())
        self.assertNotEqual(text, "invalid scope")


if __name__ == "__main__":
    unittest.main()
