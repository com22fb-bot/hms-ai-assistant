"""Yahoo IMAP con contraseña de app: config, errores y cifrado."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault(
    "OAUTH_ENCRYPTION_KEY",
    "test-oauth-encryption-key-32chars!!",
)

from app.api.auth import google_oauth_readiness
from app.security.donexto_verified import OAUTH_SIGNUP_VIA
from app.services.imap_provider import YAHOO_IMAP
from app.services.yahoo_imap import (
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
