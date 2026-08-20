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

from app.api.yahoo_mail import YahooConnectRequest, yahoo_enter
from app.middleware.authentication_context import AuthenticationContextMiddleware
from app.services.yahoo_imap import YahooImapError
from app.services.yahoo_session import _already_registered, _session_payload


class _FakeRequest:
    def __init__(self, path: str, method: str = "POST") -> None:
        self.method = method
        self.url = SimpleNamespace(path=path)
        self.client = SimpleNamespace(host="127.0.0.1")


class YahooEnterTests(unittest.TestCase):
    def test_enter_path_is_public(self) -> None:
        request = _FakeRequest("/auth/yahoo/enter")
        self.assertFalse(
            AuthenticationContextMiddleware._requires_identity(request)
        )
        connect = _FakeRequest("/auth/yahoo/connect")
        self.assertTrue(
            AuthenticationContextMiddleware._requires_identity(connect)
        )

    def test_imap_failure_does_not_touch_supabase(self) -> None:
        payload = YahooConnectRequest(
            email="hsalcidor@yahoo.com",
            app_password="clave-yahoo-1",
        )
        request = _FakeRequest("/auth/yahoo/enter")
        with patch(
            "app.api.yahoo_mail.verify_yahoo_login",
            side_effect=YahooImapError(
                "Yahoo no aceptó el correo o la clave."
            ),
        ), patch(
            "app.api.yahoo_mail.mint_yahoo_session_or_http"
        ) as mint, patch(
            "app.api.yahoo_mail.persist_yahoo_mailbox"
        ) as persist:
            with self.assertRaises(HTTPException) as caught:
                yahoo_enter(payload, request)  # type: ignore[arg-type]
            self.assertEqual(caught.exception.status_code, 400)
            mint.assert_not_called()
            persist.assert_not_called()

    def test_enter_mints_session_after_imap(self) -> None:
        payload = YahooConnectRequest(
            email="hsalcidor@yahoo.com",
            app_password="clave-yahoo-1",
        )
        request = _FakeRequest("/auth/yahoo/enter")
        with patch(
            "app.api.yahoo_mail.verify_yahoo_login"
        ), patch(
            "app.api.yahoo_mail.mint_yahoo_session_or_http",
            return_value={
                "access_token": "access-1",
                "refresh_token": "refresh-1",
                "expires_in": "3600",
                "user_id": "user-1",
                "workspace_id": "ws-1",
                "email": "hsalcidor@yahoo.com",
            },
        ), patch(
            "app.api.yahoo_mail.persist_yahoo_mailbox"
        ) as persist:
            response = yahoo_enter(payload, request)  # type: ignore[arg-type]
            self.assertEqual(response.access_token, "access-1")
            self.assertEqual(response.refresh_token, "refresh-1")
            self.assertEqual(response.email, "hsalcidor@yahoo.com")
            self.assertTrue(response.connected)
            persist.assert_called_once()
            kwargs = persist.call_args.kwargs
            self.assertEqual(kwargs["user_id"], "user-1")
            self.assertEqual(kwargs["workspace_id"], "ws-1")
            self.assertEqual(kwargs["address"], "hsalcidor@yahoo.com")
            self.assertEqual(kwargs["app_password"], "clave-yahoo-1")

    def test_session_payload_requires_both_tokens(self) -> None:
        self.assertEqual(_session_payload(None), {})
        self.assertEqual(
            _session_payload(SimpleNamespace(session=None)),
            {},
        )
        minted = _session_payload(
            SimpleNamespace(
                session=SimpleNamespace(
                    access_token="a",
                    refresh_token="r",
                    expires_in=120,
                )
            )
        )
        self.assertEqual(minted["access_token"], "a")
        self.assertEqual(minted["refresh_token"], "r")
        self.assertEqual(minted["expires_in"], "120")

    def test_already_registered_detects_duplicate(self) -> None:
        self.assertTrue(
            _already_registered(RuntimeError("User already registered"))
        )
        self.assertFalse(_already_registered(RuntimeError("network down")))


if __name__ == "__main__":
    unittest.main()
