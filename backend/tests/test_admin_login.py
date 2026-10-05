"""Owner login for /admin: mailed one-time link, never the Gmail consent flow."""

from __future__ import annotations

import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.admin_login import admin_return_url, router as admin_login_router
from app.middleware.authentication_context import AuthenticationContextMiddleware
from app.security.rate_limit import _hits
from app.services.donexto_verification_email import (
    VerificationEmailUserNotFound,
    send_admin_login_email,
)

ORIGINS = ["https://app.donexto.com", "https://www.donexto.com", "https://donexto.com"]


def _app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(AuthenticationContextMiddleware)
    app.include_router(admin_login_router)

    @app.get("/admin/overview")
    def overview() -> dict[str, str]:  # pragma: no cover - must stay protected
        return {"status": "leaked"}

    return app


class AdminLoginEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        for key in list(_hits):
            if str(key).startswith("admin-login"):
                del _hits[key]
        self.settings = patch("app.security.redirect.settings", SimpleNamespace(frontend_origins=ORIGINS))
        self.settings.start()
        self.env = patch.dict(os.environ, {"ADMIN_EMAILS": "owner@example.test"})
        self.env.start()
        self.client_patch = patch("app.api.admin_login.get_supabase_client", return_value=MagicMock())
        self.client_patch.start()
        self.send = patch("app.api.admin_login.send_admin_login_email")
        self.sent = self.send.start()
        self.http = TestClient(_app())

    def tearDown(self) -> None:
        patch.stopall()

    def test_public_and_admin_gets_link_to_admin(self) -> None:
        response = self.http.post(
            "/admin/login-link",
            json={"email": " Owner@Example.test ", "return_to": "https://www.donexto.com/admin"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "sent"})
        self.sent.assert_called_once()
        self.assertEqual(self.sent.call_args.kwargs["email"], "owner@example.test")
        self.assertEqual(self.sent.call_args.kwargs["redirect_to"], "https://www.donexto.com/admin")

    def test_non_admin_gets_same_answer_and_no_mail(self) -> None:
        response = self.http.post("/admin/login-link", json={"email": "someone@example.test"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "sent"})
        self.sent.assert_not_called()

    def test_delivery_failure_does_not_reveal_admin(self) -> None:
        self.sent.side_effect = RuntimeError("relay down")
        response = self.http.post("/admin/login-link", json={"email": "owner@example.test"})
        self.assertEqual(response.json(), {"status": "sent"})

    def test_rate_limited_per_email(self) -> None:
        for _ in range(3):
            self.assertEqual(self.http.post("/admin/login-link", json={"email": "owner@example.test"}).status_code, 200)
        self.assertEqual(self.http.post("/admin/login-link", json={"email": "owner@example.test"}).status_code, 429)

    def test_other_admin_routes_stay_protected(self) -> None:
        response = self.http.get("/admin/overview")
        self.assertIn(response.status_code, {401, 403})
        self.assertNotIn("leaked", response.text)


class AdminReturnUrlTests(unittest.TestCase):
    def test_always_lands_on_admin(self) -> None:
        with patch("app.security.redirect.settings", SimpleNamespace(frontend_origins=ORIGINS)):
            self.assertEqual(admin_return_url("https://www.donexto.com/admin"), "https://www.donexto.com/admin")
            self.assertEqual(admin_return_url("https://donexto.com/admin/"), "https://donexto.com/admin")
            self.assertEqual(admin_return_url("https://app.donexto.com/"), "https://app.donexto.com/admin")
            self.assertTrue(admin_return_url("https://evil.example/admin").endswith("donexto.com/admin"))
            self.assertTrue(admin_return_url(None).endswith("/admin"))


class AdminLoginEmailTests(unittest.TestCase):
    def test_unknown_user_gets_no_link(self) -> None:
        client = MagicMock()
        client.auth.admin.list_users.return_value = SimpleNamespace(users=[])
        client.auth.admin.get_user_by_email.side_effect = RuntimeError("missing")
        with self.assertRaises(VerificationEmailUserNotFound):
            send_admin_login_email(client=client, email="nobody@example.test", redirect_to="https://www.donexto.com/admin")
        client.auth.admin.generate_link.assert_not_called()

    def test_link_points_to_admin_with_token_hash(self) -> None:
        client = MagicMock()
        client.auth.admin.get_user_by_email.side_effect = RuntimeError("missing")
        client.auth.admin.list_users.return_value = SimpleNamespace(
            users=[SimpleNamespace(id="u1", email="owner@example.test", email_confirmed_at="2026-01-01")]
        )
        client.auth.admin.generate_link.return_value = SimpleNamespace(
            properties={"hashed_token": "hash-1", "verification_type": "magiclink"}
        )
        with patch("app.services.support_notify.send_transactional_email", return_value=True) as deliver:
            message = send_admin_login_email(
                client=client, email="owner@example.test", redirect_to="https://www.donexto.com/admin"
            )
        self.assertIn("https://www.donexto.com/admin?donexto_verify=1&token_hash=hash-1&type=magiclink", message.body)
        self.assertIn("Entrar al panel", message.html)
        self.assertNotIn("gmail.readonly", message.body)
        self.assertEqual(client.auth.admin.generate_link.call_args.args[0]["type"], "magiclink")
        client.auth.sign_in_with_otp.assert_not_called()
        deliver.assert_called_once()


class BrandedGoogleRedirectTests(unittest.TestCase):
    def test_env_status_accepts_donexto_callback(self) -> None:
        from app.api.system import env_status

        env = {
            "GOOGLE_CLIENT_ID": "x",
            "GOOGLE_CLIENT_SECRET": "y",
            "GOOGLE_REDIRECT_URI": "https://app.donexto.com/api/hms/auth/google/callback",
            "FRONTEND_ORIGINS": "https://app.donexto.com",
            "OAUTH_ENCRYPTION_KEY": "test-oauth-encryption-key-32chars!!",
        }
        with patch.dict(os.environ, env):
            shape = env_status()["oauth_shape"]
        self.assertTrue(shape["redirect_is_donexto_callback"])
        self.assertFalse(shape["redirect_is_railway_callback"])
        self.assertTrue(shape["ready_for_donexto_gmail"])

    def test_token_exchange_url_uses_branded_callback(self) -> None:
        from app.api.auth import _public_request_url

        request = SimpleNamespace(url=SimpleNamespace(query="code=abc&state=s", path="/auth/google/callback"), headers={})
        with patch.dict(os.environ, {"GOOGLE_REDIRECT_URI": "https://app.donexto.com/api/hms/auth/google/callback"}):
            self.assertEqual(
                _public_request_url(request),
                "https://app.donexto.com/api/hms/auth/google/callback?code=abc&state=s",
            )


if __name__ == "__main__":
    unittest.main()
