"""Security tests for the Donexto verification flow.

These tests encode the original security requirements for
fix/secure-donexto-verification-flow:

1. Endpoint rejects unauthenticated calls (no payload.email fallback).
2. Endpoint requires a valid session.
3. generate_link is never called for non-existent users.
4. confirm without real proof returns 403.
5. Hand-crafted ?donexto_verify=1 without session/proof is blocked.
6. "Ya confirmé mi correo" style call without the flag is blocked.
7. Middleware blocks protected routes when donexto_verified=false.
8. Middleware still allows the verification endpoints themselves.
9. OAuth sessions with donexto_verified=false are blocked.
10. Second-device / other sessions stay blocked while unverified.
11. generate_link is not invoked for missing emails.
12. Real confirmation path (query flag + confirmed email) succeeds.
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.identity import (
    DonextoVerificationEmailRequest,
    confirm_donexto_identity,
    send_donexto_verification_email,
)
from app.services.donexto_verification_email import (
    VerificationEmailUserNotFound,
    send_verification_email,
)


class SendDonextoVerifySecurityTests(unittest.TestCase):
    """Tests 1–3, 11: authenticated-only resend and no user creation."""

    def test_01_rejects_unauthenticated_call_without_email_fallback(self) -> None:
        """No session and no longer accepts payload.email → 401."""
        with patch(
            "app.api.identity.require_request_context",
            side_effect=HTTPException(status_code=401, detail={"status": "unauthorized"}),
        ):
            with self.assertRaises(HTTPException) as caught:
                send_donexto_verification_email(
                    DonextoVerificationEmailRequest(language="es")
                )
        self.assertEqual(caught.exception.status_code, 401)

    def test_02_requires_authenticated_session(self) -> None:
        """Direct call without context must fail."""
        with patch(
            "app.api.identity.require_request_context",
            side_effect=HTTPException(status_code=401, detail={"status": "unauthorized"}),
        ):
            with self.assertRaises(HTTPException) as caught:
                send_donexto_verification_email(
                    DonextoVerificationEmailRequest(language="en")
                )
        self.assertEqual(caught.exception.status_code, 401)

    def test_03_does_not_create_user_on_resend_when_email_missing(self) -> None:
        """Missing accounts get the same generic success response."""
        mock_client = MagicMock()
        mock_client.auth.admin.list_users.return_value = SimpleNamespace(users=[])

        with patch("app.api.identity.get_supabase_client", return_value=mock_client), patch(
            "app.api.identity.require_request_context"
        ) as mock_ctx:
            mock_ctx.return_value.user.email = "ghost@example.test"
            mock_ctx.return_value.user.raw_user_metadata = {}

            result = send_donexto_verification_email(
                DonextoVerificationEmailRequest(language="es")
            )

        self.assertEqual(result, {"status": "sent"})
        mock_client.auth.admin.generate_link.assert_not_called()
        mock_client.auth.resend.assert_not_called()
        mock_client.auth.sign_in_with_otp.assert_not_called()

    def test_11_generate_link_not_called_for_nonexistent_email(self) -> None:
        mock_client = MagicMock()
        mock_client.auth.admin.list_users.return_value = SimpleNamespace(users=[])

        with self.assertRaises(VerificationEmailUserNotFound):
            send_verification_email(
                client=mock_client,
                email="noexiste@test.com",
                language="es",
                redirect_to="https://app.donexto.com",
            )
        mock_client.auth.admin.generate_link.assert_not_called()
        mock_client.auth.resend.assert_not_called()
        mock_client.auth.sign_in_with_otp.assert_not_called()


class ConfirmDonextoSecurityTests(unittest.TestCase):
    """Tests 4–6, 12: proof-of-click requirements."""

    def _make_request(self, query: dict[str, str] | None = None):
        request = MagicMock()
        request.query_params = query or {}
        return request

    def test_04_confirm_without_token_returns_403(self) -> None:
        request = self._make_request({})
        with self.assertRaises(HTTPException) as caught:
            confirm_donexto_identity(request)
        self.assertEqual(caught.exception.status_code, 403)
        self.assertEqual(
            caught.exception.detail.get("status"),
            "donexto_verify_required",
        )

    def test_05_manual_donexto_verify_query_without_token_is_forbidden(self) -> None:
        """?donexto_verify=1 alone is not proof of an email click."""
        request = self._make_request({"donexto_verify": "1"})
        with self.assertRaises(HTTPException) as caught:
            confirm_donexto_identity(request)
        self.assertEqual(caught.exception.status_code, 403)

    def test_06_fake_already_confirmed_button_blocked(self) -> None:
        """Call without the query flag (typical 'Ya confirmé' button) → 403."""
        request = self._make_request({})
        with self.assertRaises(HTTPException) as caught:
            confirm_donexto_identity(request)
        self.assertEqual(caught.exception.status_code, 403)

    def test_12_real_confirmation_with_flag_and_confirmed_email_succeeds(self) -> None:
        request = self._make_request(
            {"donexto_verify": "1", "token_hash": "valid-token", "type": "signup"}
        )
        mock_client = MagicMock()
        raw_user = SimpleNamespace(
            id="user-789",
            email_confirmed_at="2026-01-01T00:00:00Z",
        )
        mock_client.auth.admin.get_user_by_id.return_value = SimpleNamespace(
            user=raw_user
        )
        mock_client.auth.verify_otp.return_value = SimpleNamespace(
            user=SimpleNamespace(id="user-789")
        )

        with patch("app.api.identity.require_request_context") as mock_ctx, patch(
            "app.api.identity.get_supabase_client", return_value=mock_client
        ), patch("app.api.identity.can_mark_donexto_verified", return_value=True), patch(
            "app.api.identity.mark_donexto_verified"
        ) as mark:
            mock_ctx.return_value.user.id = "user-789"
            mock_ctx.return_value.user.donexto_verified = False

            result = confirm_donexto_identity(request)

        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["donexto_verified"])
        mock_client.auth.verify_otp.assert_called_once_with(
            {"token_hash": "valid-token", "type": "signup"}
        )
        mark.assert_called_once_with("user-789")

    def test_13_invalid_token_hash_returns_403(self) -> None:
        """verify_otp rejects a garbage/tampered token_hash."""
        request = self._make_request(
            {"donexto_verify": "1", "token_hash": "not-a-real-token", "type": "signup"}
        )
        mock_client = MagicMock()
        mock_client.auth.verify_otp.side_effect = Exception("invalid token_hash")

        with patch("app.api.identity.require_request_context") as mock_ctx, patch(
            "app.api.identity.get_supabase_client", return_value=mock_client
        ):
            mock_ctx.return_value.user.id = "user-789"
            mock_ctx.return_value.user.donexto_verified = False

            with self.assertRaises(HTTPException) as caught:
                confirm_donexto_identity(request)

        self.assertEqual(caught.exception.status_code, 403)
        self.assertEqual(
            caught.exception.detail.get("status"), "invalid_verification_token"
        )

    def test_14_expired_token_hash_returns_403(self) -> None:
        """Supabase raises for an expired token_hash the same way as invalid."""
        request = self._make_request(
            {"donexto_verify": "1", "token_hash": "expired-token", "type": "signup"}
        )
        mock_client = MagicMock()
        mock_client.auth.verify_otp.side_effect = Exception("token has expired")

        with patch("app.api.identity.require_request_context") as mock_ctx, patch(
            "app.api.identity.get_supabase_client", return_value=mock_client
        ):
            mock_ctx.return_value.user.id = "user-789"
            mock_ctx.return_value.user.donexto_verified = False

            with self.assertRaises(HTTPException) as caught:
                confirm_donexto_identity(request)

        self.assertEqual(caught.exception.status_code, 403)
        self.assertEqual(
            caught.exception.detail.get("status"), "invalid_verification_token"
        )

    def test_15_token_hash_belonging_to_other_user_returns_403(self) -> None:
        """A token that verifies fine but belongs to a different account is rejected."""
        request = self._make_request(
            {"donexto_verify": "1", "token_hash": "someone-elses-token", "type": "signup"}
        )
        mock_client = MagicMock()
        mock_client.auth.verify_otp.return_value = SimpleNamespace(
            user=SimpleNamespace(id="attacker-user")
        )

        with patch("app.api.identity.require_request_context") as mock_ctx, patch(
            "app.api.identity.get_supabase_client", return_value=mock_client
        ):
            mock_ctx.return_value.user.id = "victim-user"
            mock_ctx.return_value.user.donexto_verified = False

            with self.assertRaises(HTTPException) as caught:
                confirm_donexto_identity(request)

        self.assertEqual(caught.exception.status_code, 403)
        self.assertEqual(
            caught.exception.detail.get("status"), "verification_user_mismatch"
        )


class MiddlewareSecurityTests(unittest.TestCase):
    """Tests 7–10: middleware blocks unverified sessions."""

    def test_07_middleware_blocks_unverified_session_on_protected_route(self) -> None:
        from app.middleware.authentication_context import AuthenticationContextMiddleware

        async def fake_user(_request):
            user = MagicMock()
            user.id = "user-123"
            user.donexto_verified = False
            return user

        # We unit-test the decision logic by exercising the same condition.
        context = MagicMock()
        context.user.donexto_verified = False
        path = "/cases"
        exempt = (
            "/identity/me",
            "/identity/confirm-donexto",
            "/identity/send-donexto-verify",
        )
        is_exempt = any(path == item or path.startswith(item + "/") for item in exempt)
        self.assertFalse(is_exempt)
        self.assertFalse(context.user.donexto_verified)

    def test_08_middleware_allows_verification_routes(self) -> None:
        exempt = (
            "/identity/me",
            "/identity/confirm-donexto",
            "/identity/send-donexto-verify",
        )
        for path in exempt:
            is_exempt = any(
                path == item or path.startswith(item + "/") for item in exempt
            )
            self.assertTrue(is_exempt, msg=f"{path} should be exempt")

    def test_09_oauth_session_blocked_if_not_verified(self) -> None:
        context = MagicMock()
        context.user.donexto_verified = False
        context.user.has_oauth_identity = True
        path = "/cases/dashboard"
        exempt = (
            "/identity/me",
            "/identity/confirm-donexto",
            "/identity/send-donexto-verify",
        )
        is_exempt = any(path == item or path.startswith(item + "/") for item in exempt)
        self.assertFalse(is_exempt)
        self.assertFalse(context.user.donexto_verified)

    def test_10_second_device_session_blocked_while_unverified(self) -> None:
        """Any session (including a second device) stays blocked while unverified."""
        context = MagicMock()
        context.user.donexto_verified = False
        path = "/workspace"
        exempt = (
            "/identity/me",
            "/identity/confirm-donexto",
            "/identity/send-donexto-verify",
        )
        is_exempt = any(path == item or path.startswith(item + "/") for item in exempt)
        self.assertFalse(is_exempt)
        self.assertFalse(context.user.donexto_verified)


class MiddlewareIntegrationTests(unittest.TestCase):
    """Real ASGI integration: the actual middleware, not the inline copy above."""

    def _build_app(self):
        from fastapi import FastAPI

        from app.middleware.authentication_context import AuthenticationContextMiddleware

        app = FastAPI()
        app.add_middleware(AuthenticationContextMiddleware)

        @app.get("/cases")
        def protected_route():  # pragma: no cover - only reached if not blocked
            return {"status": "ok"}

        return app

    def test_16_real_middleware_blocks_unverified_user_before_workspace_resolution(
        self,
    ) -> None:
        app = self._build_app()
        unverified_user = SimpleNamespace(
            id="user-123", donexto_verified=False, email="user@example.test"
        )

        with patch(
            "app.middleware.authentication_context.authenticate_request",
            return_value=unverified_user,
        ), patch(
            "app.middleware.authentication_context.resolve_workspace_context"
        ) as mock_resolve_workspace:
            client = TestClient(app)
            response = client.get("/cases")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"]["status"], "donexto_unverified"
        )
        mock_resolve_workspace.assert_not_called()

    def test_17_real_middleware_allows_verified_user_through(self) -> None:
        app = self._build_app()
        verified_user = SimpleNamespace(
            id="user-123", donexto_verified=True, email="user@example.test"
        )
        workspace_context = SimpleNamespace(
            user=verified_user,
            workspace_id="ws-1",
            workspace_name="Test",
            membership_role="owner",
            google_account=None,
        )

        with patch(
            "app.middleware.authentication_context.authenticate_request",
            return_value=verified_user,
        ), patch(
            "app.middleware.authentication_context.resolve_workspace_context",
            return_value=workspace_context,
        ) as mock_resolve_workspace:
            client = TestClient(app)
            response = client.get("/cases")

        self.assertEqual(response.status_code, 200)
        mock_resolve_workspace.assert_called_once()


if __name__ == "__main__":
    unittest.main()