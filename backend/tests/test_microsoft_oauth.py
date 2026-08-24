"""Microsoft / Outlook / Hotmail: dominios y URL OAuth."""

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

from app.api.login_resolve import resolve_mailbox_provider
from app.middleware.authentication_context import AuthenticationContextMiddleware
from app.security.identity import MAILBOX_PROVIDERS
from app.services.microsoft_domains import is_microsoft_mail_address
from app.services.microsoft_oauth import (
    build_microsoft_authorization_url,
    granted_microsoft_mail_read,
    microsoft_authorize_scopes,
    microsoft_email_from_profile,
    microsoft_oauth_tenant,
    microsoft_tenant_from_state,
)


class _FakeRequest:
    def __init__(self, path: str, method: str = "POST") -> None:
        self.method = method
        self.url = type("U", (), {"path": path})()
        self.client = type("C", (), {"host": "127.0.0.1"})()
        self.headers = {}


class MicrosoftOAuthTests(unittest.TestCase):
    def test_login_and_callback_are_public(self) -> None:
        login = _FakeRequest("/auth/microsoft/login")
        callback = _FakeRequest("/auth/microsoft/callback", method="GET")
        self.assertFalse(
            AuthenticationContextMiddleware._requires_identity(login)
        )
        self.assertFalse(
            AuthenticationContextMiddleware._requires_identity(callback)
        )

    def test_consumer_and_365_domains(self) -> None:
        self.assertTrue(is_microsoft_mail_address("ana@hotmail.com"))
        self.assertTrue(is_microsoft_mail_address("ana@hotmail.com.mx"))
        self.assertTrue(is_microsoft_mail_address("ana@outlook.com"))
        self.assertTrue(is_microsoft_mail_address("ana@outlook.com.mx"))
        self.assertTrue(is_microsoft_mail_address("ana@msn.com"))
        self.assertTrue(is_microsoft_mail_address("ana@hotmail.es"))
        from app.services.microsoft_domains import MICROSOFT_MAIL_DOMAINS

        self.assertEqual(
            MICROSOFT_MAIL_DOMAINS,
            (
                "hotmail.com",
                "hotmail.es",
                "hotmail.com.mx",
                "outlook.com",
                "outlook.es",
                "outlook.com.mx",
                "live.com",
                "live.com.mx",
                "msn.com",
                "onmicrosoft.com",
            ),
        )
        self.assertTrue(is_microsoft_mail_address("ana@contoso.onmicrosoft.com"))
        self.assertFalse(is_microsoft_mail_address("ana@empresa.mx"))
        self.assertEqual(resolve_mailbox_provider("x@outlook.com.mx"), "hotmail")
        self.assertEqual(
            resolve_mailbox_provider("x@contoso.onmicrosoft.com"), "hotmail"
        )
        self.assertIn("microsoft", MAILBOX_PROVIDERS)

    def test_authorization_url(self) -> None:
        with patch("app.services.microsoft_oauth.settings") as settings:
            settings.azure_client_id = "azure-id"
            settings.azure_client_secret = "secret"
            settings.azure_redirect_uri = (
                "https://hms-ai-assistant-production.up.railway.app"
                "/auth/microsoft/callback"
            )
            url = build_microsoft_authorization_url(
                "login.state-token",
                login_hint="ana@outlook.com.mx",
            )
        self.assertIn("login.microsoftonline.com/consumers/", url)
        self.assertIn("client_id=azure-id", url)
        self.assertIn("Mail.Read", url)
        self.assertIn("login_hint=ana%40outlook.com.mx", url)
        self.assertIn("prompt=select_account", url)

    def test_requires_entra_app(self) -> None:
        from app.api.microsoft_mail import microsoft_login

        with patch("app.services.microsoft_oauth.settings") as settings:
            settings.azure_client_id = ""
            settings.azure_client_secret = ""
            settings.azure_redirect_uri = ""
            with self.assertRaises(HTTPException) as caught:
                microsoft_login(_FakeRequest("/auth/microsoft/login"), None)
        self.assertEqual(caught.exception.status_code, 503)
        self.assertIn(
            "microsoft_oauth_not_configured",
            str(caught.exception.detail),
        )

    def test_login_rejects_unknown_hint(self) -> None:
        from app.api.microsoft_mail import MicrosoftLoginRequest, microsoft_login

        with (
            patch("app.api.microsoft_mail.require_microsoft_oauth_config"),
            patch("app.api.microsoft_mail.auth_user_exists", return_value=False),
        ):
            with self.assertRaises(HTTPException) as caught:
                microsoft_login(
                    _FakeRequest("/auth/microsoft/login"),  # type: ignore[arg-type]
                    MicrosoftLoginRequest(
                        intent="login",
                        login_hint="nadie@outlook.com",
                    ),
                )
        self.assertEqual(caught.exception.status_code, 403)

    def test_mail_read_and_email(self) -> None:
        self.assertTrue(
            granted_microsoft_mail_read({"scope": "openid Mail.Read User.Read"})
        )
        self.assertTrue(
            granted_microsoft_mail_read(
                {"scope": "openid https://graph.microsoft.com/Mail.Read"}
            )
        )
        self.assertFalse(
            granted_microsoft_mail_read({"scope": "openid User.Read"})
        )
        self.assertEqual(
            microsoft_email_from_profile(
                {"mail": None, "userPrincipalName": "Ana@Outlook.Com"}
            ),
            "ana@outlook.com",
        )
        self.assertIn("Mail.Read", microsoft_authorize_scopes())

    def test_hotmail_uses_consumers_tenant(self) -> None:
        self.assertEqual(
            microsoft_oauth_tenant("donexto@hotmail.com"),
            "consumers",
        )
        self.assertEqual(microsoft_oauth_tenant("ana@contoso.onmicrosoft.com"), "common")
        self.assertEqual(
            microsoft_tenant_from_state("signup.consumers.abc"),
            "consumers",
        )

    def test_callback_missing_code_redirects_home(self) -> None:
        from fastapi.responses import RedirectResponse
        from app.api.microsoft_mail import microsoft_callback

        response = microsoft_callback(
            SimpleNamespace(query_params={})  # type: ignore[arg-type]
        )
        self.assertIsInstance(response, RedirectResponse)
        self.assertEqual(response.status_code, 302)
        location = str(response.headers.get("location") or response.url)
        self.assertIn("https://app.donexto.com", location)
        self.assertIn("donexto=microsoft_error", location)
        self.assertNotIn("technical_detail", location)

    def test_callback_used_state_redirects_home(self) -> None:
        from fastapi.responses import RedirectResponse
        from app.api.microsoft_mail import microsoft_callback
        from app.services.oauth_storage import OAuthStateError

        request = SimpleNamespace(
            query_params={
                "state": "login.consumers.used",
                "code": "auth-code",
            }
        )
        with patch("app.api.microsoft_mail.oauth_storage") as storage:
            storage.load_oauth_state.side_effect = OAuthStateError(
                "El estado OAuth no existe, ya fue utilizado o no corresponde "
                "al proveedor."
            )
            response = microsoft_callback(request)  # type: ignore[arg-type]

        self.assertIsInstance(response, RedirectResponse)
        self.assertEqual(response.status_code, 302)
        location = str(response.headers.get("location") or response.url)
        self.assertIn("https://app.donexto.com", location)
        self.assertIn("donexto=microsoft_error", location)
        self.assertIn("reason=", location)
        self.assertNotIn("technical_detail", location)
        storage.consume_oauth_state.assert_not_called()
        storage.delete_oauth_state.assert_not_called()

    def test_callback_storage_error_redirects_home(self) -> None:
        from fastapi.responses import RedirectResponse
        from app.api.microsoft_mail import microsoft_callback
        from app.services.oauth_storage import OAuthStorageError

        request = SimpleNamespace(
            query_params={
                "state": "login.consumers.token",
                "code": "auth-code",
            }
        )
        with patch("app.api.microsoft_mail.oauth_storage") as storage:
            storage.load_oauth_state.side_effect = OAuthStorageError(
                "Supabase no responde"
            )
            response = microsoft_callback(request)  # type: ignore[arg-type]

        location = str(response.headers.get("location") or response.url)
        self.assertIsInstance(response, RedirectResponse)
        self.assertIn("donexto=microsoft_error", location)

    def test_callback_login_existing_deletes_state_after_token(self) -> None:
        from fastapi.responses import RedirectResponse
        from app.api.microsoft_mail import microsoft_callback

        request = SimpleNamespace(
            query_params={
                "state": "login.consumers.token",
                "code": "auth-code",
            }
        )
        with (
            patch("app.api.microsoft_mail.oauth_storage") as storage,
            patch(
                "app.api.microsoft_mail.exchange_microsoft_code",
                return_value={
                    "access_token": "ms-at",
                    "refresh_token": "ms-rt",
                    "expires_in": 3600,
                    "scope": "openid Mail.Read User.Read",
                },
            ),
            patch(
                "app.api.microsoft_mail.fetch_microsoft_profile",
                return_value={"mail": "donexto@hotmail.com"},
            ),
            patch(
                "app.api.microsoft_mail.microsoft_email_from_profile",
                return_value="donexto@hotmail.com",
            ),
            patch("app.api.microsoft_mail.auth_user_exists", return_value=True),
            patch("app.api.microsoft_mail.mint_yahoo_session_or_http") as mint,
            patch("app.api.microsoft_mail.persist_microsoft_mailbox") as persist,
            patch(
                "app.api.microsoft_mail.sanitize_return_to",
                return_value="https://app.donexto.com/",
            ),
        ):
            storage.load_oauth_state.return_value = {
                "return_to": "https://app.donexto.com/",
            }
            mint.return_value = {
                "user_id": "u1",
                "workspace_id": "w1",
                "access_token": "at",
                "refresh_token": "rt",
                "expires_in": "3600",
            }
            response = microsoft_callback(request)  # type: ignore[arg-type]

        self.assertIsInstance(response, RedirectResponse)
        location = str(response.headers.get("location") or response.url)
        self.assertIn("access_token=at", location)
        storage.load_oauth_state.assert_called_once_with(
            "login.consumers.token",
            "microsoft",
        )
        storage.consume_oauth_state.assert_not_called()
        storage.delete_oauth_state.assert_called_once_with("login.consumers.token")
        persist.assert_called_once()

    def test_callback_token_error_keeps_state(self) -> None:
        from fastapi.responses import RedirectResponse
        from app.api.microsoft_mail import microsoft_callback
        from app.services.microsoft_oauth import MicrosoftOAuthError

        request = SimpleNamespace(
            query_params={
                "state": "login.consumers.token",
                "code": "auth-code",
            }
        )
        with (
            patch("app.api.microsoft_mail.oauth_storage") as storage,
            patch(
                "app.api.microsoft_mail.exchange_microsoft_code",
                side_effect=MicrosoftOAuthError("token inválido"),
            ),
        ):
            storage.load_oauth_state.return_value = {
                "return_to": "https://app.donexto.com/",
            }
            response = microsoft_callback(request)  # type: ignore[arg-type]

        self.assertIsInstance(response, RedirectResponse)
        location = str(response.headers.get("location") or response.url)
        self.assertIn("donexto=microsoft_error", location)
        storage.delete_oauth_state.assert_not_called()


if __name__ == "__main__":
    unittest.main()
