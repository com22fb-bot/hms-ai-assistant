"""Yahoo IMAP con contraseña de app: config, errores y cifrado."""

from __future__ import annotations

import imaplib
import os
import socket
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault(
    "OAUTH_ENCRYPTION_KEY",
    "test-oauth-encryption-key-32chars!!",
)

from app.api.auth import (
    GooglePublicLoginRequest,
    google_oauth_readiness,
    google_public_login,
    google_token_redirect_target,
)
from app.security.donexto_verified import OAUTH_SIGNUP_VIA
from app.services.imap_mail import ImapMailError, open_imap_client
from app.services.imap_provider import ICLOUD_IMAP, YAHOO_IMAP
from app.services.yahoo_imap import (
    YahooImapError,
    _open_yahoo_client,
    classify_yahoo_app_error,
    looks_like_yahoo_app_password,
    verify_yahoo_app_login,
)


class YahooAppImapConfigTest(unittest.TestCase):
    def test_server_is_ssl_993(self) -> None:
        self.assertEqual(YAHOO_IMAP.host, "imap.mail.yahoo.com")
        self.assertEqual(YAHOO_IMAP.port, 993)

    def test_signup_via_does_not_skip_donexto_email(self) -> None:
        self.assertNotIn("yahoo_imap", OAUTH_SIGNUP_VIA)
        self.assertNotIn("gmail_oauth", OAUTH_SIGNUP_VIA)
        self.assertNotIn("icloud_imap", OAUTH_SIGNUP_VIA)

    def test_app_password_shape(self) -> None:
        self.assertTrue(looks_like_yahoo_app_password("abcd efgh ijkl mnop"))
        self.assertFalse(looks_like_yahoo_app_password("mi-clave-de-yahoo"))

    def test_regular_password_asks_for_app_password(self) -> None:
        error = classify_yahoo_app_error(
            "AUTHENTICATIONFAILED",
            "mi-clave-larga",
        )
        self.assertEqual(error.code, "app_password_required")
        self.assertNotIn("mi-clave-larga", str(error))

    def test_bad_app_password(self) -> None:
        error = classify_yahoo_app_error(
            "AUTHENTICATIONFAILED",
            "abcdefghijklmnop",
        )
        self.assertEqual(error.code, "wrong_password")

    def test_verify_uses_readonly_select(self) -> None:
        calls: list[tuple] = []

        class _Client:
            def select(self, mailbox, readonly=False):
                calls.append((mailbox, readonly))
                return "OK", [b"1"]

            def logout(self):
                return "BYE", []

        with patch(
            "app.services.yahoo_imap._open_yahoo_client",
            return_value=_Client(),
        ):
            self.assertEqual(
                verify_yahoo_app_login("ana@yahoo.com", "abcdefghijklmnop"),
                "ana@yahoo.com",
            )
        self.assertEqual(calls, [("INBOX", True)])

    def test_google_readiness_lists_names_not_secrets(self) -> None:
        with patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "", "GOOGLE_CLIENT_SECRET": "", "GOOGLE_REDIRECT_URI": ""}, clear=False):
            payload = google_oauth_readiness()
        self.assertFalse(payload["configured"])
        self.assertEqual(
            payload["missing_variables"],
            ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REDIRECT_URI"],
        )
        blob = str(payload)
        self.assertNotIn("client_secret_value", blob)
        self.assertIn("gmail.readonly", blob)

    def test_rejected_app_password_is_classified_not_raw_imap(self) -> None:
        class _Boom:
            def login(self, _user: str, _password: str):
                raise imaplib.IMAP4.error(
                    b"[AUTHENTICATIONFAILED] Invalid credentials"
                )

            def logout(self):
                return "BYE", []

        with patch(
            "app.services.imap_mail.imaplib.IMAP4_SSL",
            return_value=_Boom(),
        ):
            with self.assertRaises(YahooImapError) as caught:
                _open_yahoo_client("ana@yahoo.com", "abcdefghijklmnop")
        self.assertEqual(caught.exception.code, "wrong_password")
        self.assertNotIsInstance(caught.exception.__cause__, type(None))
        self.assertNotIn("abcdefghijklmnop", str(caught.exception))

    def test_icloud_login_failure_is_imap_mail_error(self) -> None:
        class _Boom:
            def login(self, _user: str, password: str):
                raise imaplib.IMAP4.error(
                    f"[AUTHENTICATIONFAILED] {password}".encode()
                )

            def logout(self):
                return "BYE", []

        with patch(
            "app.services.imap_mail.imaplib.IMAP4_SSL",
            return_value=_Boom(),
        ):
            with self.assertRaises(ImapMailError) as caught:
                open_imap_client(
                    ICLOUD_IMAP,
                    "ana@icloud.com",
                    "abcdefghijklmnop",
                )
        self.assertEqual(caught.exception.code, "auth_failed")
        self.assertNotIn("abcdefghijklmnop", str(caught.exception))
        self.assertIsInstance(caught.exception.__cause__, imaplib.IMAP4.error)

    def test_socket_timeout_is_network_error(self) -> None:
        with patch(
            "app.services.imap_mail.imaplib.IMAP4_SSL",
            side_effect=socket.timeout("timed out"),
        ):
            with self.assertRaises(ImapMailError) as caught:
                open_imap_client(
                    YAHOO_IMAP,
                    "ana@yahoo.com",
                    "abcdefghijklmnop",
                )
        self.assertEqual(caught.exception.code, "network")
        self.assertNotIn("abcdefghijklmnop", str(caught.exception))


class GoogleReturnToTests(unittest.TestCase):
    def test_vercel_preview_cannot_receive_tokens(self) -> None:
        stolen = "https://evil-donexto.vercel.app/phish"
        with patch("app.security.redirect.settings") as settings:
            settings.frontend_origins = [
                "https://app.donexto.com",
                "https://www.donexto.com",
                "http://localhost:3000",
            ]
            target = google_token_redirect_target(stolen)
        self.assertEqual(target, "https://app.donexto.com/")
        self.assertNotIn("vercel.app", target)
        self.assertNotIn("githubpreview.dev", target)

        captured: dict[str, object] = {}

        def _capture_state(**kwargs: object) -> str:
            captured.update(kwargs)
            return "state-token"

        class _Flow:
            def authorization_url(self, **_kwargs: object):
                return "https://accounts.google.com/o/oauth2/auth", "state-token"

        request = SimpleNamespace(
            client=SimpleNamespace(host="198.51.100.8"),
            headers={"origin": stolen},
        )
        with (
            patch("app.security.redirect.settings") as settings,
            patch("app.security.rate_limit.allow_request", return_value=True),
            patch.dict(
                os.environ,
                {
                    "GOOGLE_CLIENT_ID": "test-client-id",
                    "GOOGLE_CLIENT_SECRET": "test-client-secret",
                    "GOOGLE_REDIRECT_URI": "http://localhost:8000/auth/google/callback",
                },
                clear=False,
            ),
            patch("app.api.auth.oauth_storage.create_oauth_state", _capture_state),
            patch("app.api.auth.create_google_flow", return_value=_Flow()),
        ):
            settings.frontend_origins = [
                "https://app.donexto.com",
                "https://www.donexto.com",
                "http://localhost:3000",
            ]
            google_public_login(
                request,  # type: ignore[arg-type]
                GooglePublicLoginRequest(
                    return_to=stolen,
                    login_hint="ana@gmail.com",
                ),
            )
        self.assertEqual(captured.get("return_to"), "https://app.donexto.com/")
        self.assertNotIn("vercel.app", str(captured.get("return_to")))
