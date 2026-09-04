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
            settings.yahoo_mail_read_enabled = False
            url = build_yahoo_authorization_url(
                "state-token",
                login_hint="hsalcidor@yahoo.com",
            )
            without_hint = build_yahoo_authorization_url("state-token")
            ignored = build_yahoo_authorization_url(
                "state-token",
                login_hint="not-an-email",
            )
        self.assertIn("https://api.login.yahoo.com/oauth2/request_auth", url)
        self.assertIn("client_id=client-id", url)
        self.assertIn("state=state-token", url)
        self.assertIn("openid", url)
        self.assertIn("nonce=state-token", url)
        self.assertIn("login_hint=hsalcidor%40yahoo.com", url)
        self.assertNotIn("prompt=", url)
        self.assertNotIn("mail-r", url)
        self.assertNotIn("login_hint", without_hint)
        self.assertNotIn("login_hint", ignored)

    def test_mailbox_intent_does_not_request_mail_read(self) -> None:
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
            settings.yahoo_mail_read_enabled = False
            mailbox = build_yahoo_authorization_url("mailbox.state-token")
            login = build_yahoo_authorization_url("login.state-token")
        self.assertNotIn("mail-r", mailbox)
        self.assertNotIn("mail-r", login)

    def test_mailbox_intent_requests_mail_read_only_when_enabled(self) -> None:
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
            settings.yahoo_mail_read_enabled = True
            mailbox = build_yahoo_authorization_url("mailbox.state-token")
            login = build_yahoo_authorization_url("login.state-token")
            signup = build_yahoo_authorization_url("signup.state-token")
        self.assertIn("mail-r", mailbox)
        self.assertNotIn("mail-r", login)
        self.assertNotIn("mail-r", signup)

    def test_sanitize_return_to_stays_on_donexto(self) -> None:
        with patch(
            "app.security.redirect.settings"
        ) as settings:
            settings.frontend_origins = ["https://app.donexto.com"]
            self.assertEqual(
                sanitize_return_to("https://evil.example/phish"),
                "https://app.donexto.com/",
            )
            self.assertEqual(
                sanitize_return_to("https://falsodonexto.com/phish"),
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

    def test_login_intent_rejects_unknown_yahoo_hint(self) -> None:
        from app.api.yahoo_mail import YahooLoginRequest, yahoo_login

        with (
            patch("app.api.yahoo_mail.require_yahoo_oauth_config"),
            patch("app.api.yahoo_mail.auth_user_exists", return_value=False),
        ):
            with self.assertRaises(HTTPException) as caught:
                yahoo_login(
                    _FakeRequest("/auth/yahoo/login"),  # type: ignore[arg-type]
                    YahooLoginRequest(
                        intent="login",
                        login_hint="melgibson@yahoo.com",
                    ),
                )
        self.assertEqual(caught.exception.status_code, 403)
        self.assertIn("Suscribirse", str(caught.exception.detail))

    def test_mail_read_scope_detection(self) -> None:
        self.assertTrue(granted_mail_read({"scope": "openid email mail-r"}))
        self.assertTrue(granted_mail_read({"scope": "openid,mail-w"}))
        self.assertFalse(granted_mail_read({"scope": "openid email profile"}))

    def test_invalid_scope_message_is_spanish(self) -> None:
        from app.api.yahoo_mail import _yahoo_callback_error_message

        text = _yahoo_callback_error_message("invalid_scope", "invalid scope")
        self.assertIn("buzón", text.lower())
        self.assertIn("no hace falta firmar", text.lower())
        self.assertNotEqual(text, "invalid scope")

    def test_intent_helpers(self) -> None:
        from app.services.yahoo_oauth import (
            normalize_yahoo_intent,
            yahoo_intent_from_state,
        )

        self.assertEqual(normalize_yahoo_intent(None), "login")
        self.assertEqual(normalize_yahoo_intent("mailbox"), "mailbox")
        self.assertEqual(yahoo_intent_from_state("mailbox.abc"), "mailbox")
        self.assertEqual(normalize_yahoo_intent("other"), "login")
        self.assertEqual(yahoo_intent_from_state("login.abc"), "login")
        self.assertEqual(yahoo_intent_from_state("signup.xyz"), "signup")
        self.assertEqual(yahoo_intent_from_state("plain-token"), "login")

    def test_callback_login_unknown_email_has_no_session(self) -> None:
        from fastapi.responses import RedirectResponse
        from app.api.yahoo_mail import yahoo_callback

        request = SimpleNamespace(
            query_params={"state": "login.token", "code": "auth-code"}
        )
        with (
            patch("app.api.yahoo_mail.oauth_storage") as storage,
            patch(
                "app.api.yahoo_mail.exchange_yahoo_code",
                return_value={"access_token": "ya"},
            ),
            patch("app.api.yahoo_mail.fetch_yahoo_userinfo", return_value={}),
            patch(
                "app.api.yahoo_mail.yahoo_email_from_userinfo",
                return_value="nuevo@yahoo.com",
            ),
            patch("app.api.yahoo_mail.auth_user_exists", return_value=False),
            patch("app.api.yahoo_mail.mint_yahoo_session_or_http") as mint,
            patch("app.api.yahoo_mail.persist_yahoo_mailbox") as persist,
            patch(
                "app.api.yahoo_mail.sanitize_return_to",
                return_value="https://app.donexto.com/",
            ),
        ):
            storage.consume_oauth_state.return_value = {
                "return_to": "https://app.donexto.com/",
            }
            response = yahoo_callback(request)  # type: ignore[arg-type]

        self.assertIsInstance(response, RedirectResponse)
        location = str(response.headers.get("location") or response.url)
        self.assertIn("donexto=signup", location)
        self.assertIn("reason=no_account", location)
        self.assertIn("nuevo%40yahoo.com", location)
        self.assertNotIn("access_token", location)
        mint.assert_not_called()
        persist.assert_not_called()

    def test_callback_login_existing_mints_session(self) -> None:
        from fastapi.responses import RedirectResponse
        from app.api.yahoo_mail import yahoo_callback

        request = SimpleNamespace(
            query_params={"state": "login.token", "code": "auth-code"}
        )
        with (
            patch("app.api.yahoo_mail.oauth_storage") as storage,
            patch(
                "app.api.yahoo_mail.exchange_yahoo_code",
                return_value={"access_token": "ya", "expires_in": 3600},
            ),
            patch("app.api.yahoo_mail.fetch_yahoo_userinfo", return_value={}),
            patch(
                "app.api.yahoo_mail.yahoo_email_from_userinfo",
                return_value="hsalcidor@yahoo.com",
            ),
            patch("app.api.yahoo_mail.auth_user_exists", return_value=True),
            patch("app.api.yahoo_mail.mint_yahoo_session_or_http") as mint,
            patch("app.api.yahoo_mail.persist_yahoo_mailbox") as persist,
            patch(
                "app.api.yahoo_mail.sanitize_return_to",
                return_value="https://app.donexto.com/",
            ),
        ):
            storage.consume_oauth_state.return_value = {
                "return_to": "https://app.donexto.com/",
            }
            mint.return_value = {
                "user_id": "u1",
                "workspace_id": "w1",
                "access_token": "at",
                "refresh_token": "rt",
                "expires_in": "3600",
            }
            response = yahoo_callback(request)  # type: ignore[arg-type]

        self.assertIsInstance(response, RedirectResponse)
        location = str(response.headers.get("location") or response.url)
        self.assertIn("access_token=at", location)
        self.assertIn("type=magiclink", location)
        mint.assert_called_once_with(
            "hsalcidor@yahoo.com",
            allow_create=False,
        )
        persist.assert_called_once()

    def test_callback_signup_unknown_mints_session(self) -> None:
        from fastapi.responses import RedirectResponse
        from app.api.yahoo_mail import yahoo_callback

        request = SimpleNamespace(
            query_params={"state": "signup.token", "code": "auth-code"}
        )
        with (
            patch("app.api.yahoo_mail.oauth_storage") as storage,
            patch(
                "app.api.yahoo_mail.exchange_yahoo_code",
                return_value={"access_token": "ya"},
            ),
            patch("app.api.yahoo_mail.fetch_yahoo_userinfo", return_value={}),
            patch(
                "app.api.yahoo_mail.yahoo_email_from_userinfo",
                return_value="nuevo@yahoo.com",
            ),
            patch("app.api.yahoo_mail.auth_user_exists", return_value=False),
            patch("app.api.yahoo_mail.mint_yahoo_session_or_http") as mint,
            patch("app.api.yahoo_mail.persist_yahoo_mailbox"),
            patch(
                "app.api.yahoo_mail.sanitize_return_to",
                return_value="https://app.donexto.com/",
            ),
        ):
            storage.consume_oauth_state.return_value = {
                "return_to": "https://app.donexto.com/",
            }
            mint.return_value = {
                "user_id": "u2",
                "workspace_id": "w2",
                "access_token": "at2",
                "refresh_token": "rt2",
                "expires_in": "3600",
            }
            response = yahoo_callback(request)  # type: ignore[arg-type]

        location = str(response.headers.get("location") or response.url)
        self.assertIn("access_token=at2", location)
        mint.assert_called_once_with("nuevo@yahoo.com", allow_create=True)


if __name__ == "__main__":
    unittest.main()
