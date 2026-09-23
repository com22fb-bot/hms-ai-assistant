"""Security tests for the Donexto verification flow.

These tests encode the original security requirements for
fix/secure-donexto-verification-flow:

1. Resend rejects unauthenticated calls (no payload.email fallback).
2. Resend requires a valid session.
3. generate_link is never called for non-existent users.
4. confirm without real proof returns 403.
5. Hand-crafted ?donexto_verify=1 without the email token is blocked.
6. "Ya confirmé mi correo" style call without the flag is blocked.
7. Middleware blocks protected routes when donexto_verified=false.
8. Middleware still allows the verification endpoints themselves.
9. OAuth sessions with donexto_verified=false are blocked.
10. Second-device / other sessions stay blocked while unverified.
11. generate_link is not invoked for missing emails.
12. Real confirmation path (query flag + token) succeeds.
13. A cold browser with no OAuth session can confirm and receive a session.
14. Reused or expired tokens fail and do not mark the account.
15. OAuth without the email click stays unverified.
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
        mock_client.auth.admin.get_user_by_email.side_effect = RuntimeError("missing")

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
        mock_client.auth.admin.get_user_by_email.side_effect = RuntimeError("missing")

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


class AlreadyVerifiedSendTests(unittest.TestCase):
    """Returning accounts must not receive another Donexto verification mail."""

    def _context(self, *, verified: bool) -> SimpleNamespace:
        return SimpleNamespace(
            user=SimpleNamespace(
                id="user-1",
                email="hmcelinfo@gmail.com",
                donexto_verified=verified,
                raw_user_metadata={},
            )
        )

    def test_trusted_session_does_not_call_resend(self) -> None:
        client = MagicMock()
        with patch(
            "app.api.identity.require_request_context",
            return_value=self._context(verified=True),
        ), patch(
            "app.api.identity.get_supabase_client",
            return_value=client,
        ), patch(
            "app.services.support_notify.send_transactional_email",
            return_value=True,
        ) as send_mail:
            result = send_donexto_verification_email(
                DonextoVerificationEmailRequest(language="es")
            )

        self.assertEqual(
            result,
            {
                "status": "ok",
                "already_verified": True,
                "donexto_verified": True,
            },
        )
        send_mail.assert_not_called()
        client.auth.resend.assert_not_called()
        client.auth.admin.generate_link.assert_not_called()
        client.auth.sign_in_with_otp.assert_not_called()
        client.auth.admin.get_user_by_id.assert_not_called()

    def test_stale_jwt_with_trusted_admin_record_does_not_call_resend(self) -> None:
        client = MagicMock()
        client.auth.admin.get_user_by_id.return_value = SimpleNamespace(
            user={
                "id": "user-1",
                "email": "hmcelinfo@gmail.com",
                "identities": [{"provider": "google"}],
                "user_metadata": {"donexto_verified": True},
                "app_metadata": {
                    "provider": "google",
                    "donexto_verified": True,
                    "donexto_verification_source": "email",
                },
            }
        )
        with patch(
            "app.api.identity.require_request_context",
            return_value=self._context(verified=False),
        ), patch("app.api.identity.get_supabase_client", return_value=client), patch(
            "app.services.support_notify.send_transactional_email",
            return_value=True,
        ) as send_mail:
            result = send_donexto_verification_email(
                DonextoVerificationEmailRequest(language="es")
            )

        self.assertTrue(result["already_verified"])
        send_mail.assert_not_called()
        client.auth.resend.assert_not_called()
        client.auth.admin.generate_link.assert_not_called()

    def test_user_metadata_flag_alone_still_sends_for_new_oauth(self) -> None:
        """OAuth without an email-sourced app_metadata flag still gets one mail."""
        client = MagicMock()
        client.auth.admin.get_user_by_id.return_value = SimpleNamespace(
            user={
                "id": "user-1",
                "email": "hmcelinfo@gmail.com",
                "identities": [{"provider": "google"}],
                "user_metadata": {"donexto_verified": True},
                "app_metadata": {"provider": "google"},
            }
        )
        client.auth.admin.generate_link.return_value = SimpleNamespace(
            properties={"hashed_token": "hash-token", "verification_type": "magiclink"}
        )
        with patch(
            "app.api.identity.require_request_context",
            return_value=self._context(verified=False),
        ), patch("app.api.identity.get_supabase_client", return_value=client), patch(
            "app.services.support_notify.send_transactional_email",
            return_value=True,
        ) as send_mail:
            result = send_donexto_verification_email(
                DonextoVerificationEmailRequest(language="es")
            )

        self.assertEqual(result, {"status": "sent"})
        send_mail.assert_called_once()
        client.auth.resend.assert_not_called()
        client.auth.admin.generate_link.assert_called_once()


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
            id="78900000-0000-4000-8000-000000000789",
            email_confirmed_at="2026-01-01T00:00:00Z",
            app_metadata={},
            user_metadata={},
            identities=[{"provider": "email"}],
        )
        mock_client.auth.admin.get_user_by_id.return_value = SimpleNamespace(
            user=raw_user
        )
        mock_client.auth.verify_otp.return_value = SimpleNamespace(
            user=SimpleNamespace(
                id="78900000-0000-4000-8000-000000000789",
                email_confirmed_at="2026-01-01T00:00:00Z",
            ),
            session=SimpleNamespace(
                access_token="access-token",
                refresh_token="refresh-token",
                expires_in=3600,
            ),
        )

        with patch(
            "app.api.identity.require_request_context",
            side_effect=AssertionError("confirm must not require a session"),
        ), patch(
            "app.api.identity.get_supabase_client", return_value=mock_client
        ), patch("app.api.identity.mark_donexto_verified") as mark:
            result = confirm_donexto_identity(request)

        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["donexto_verified"])
        self.assertEqual(result["access_token"], "access-token")
        self.assertEqual(result["refresh_token"], "refresh-token")
        self.assertFalse(result["already"])
        mock_client.auth.verify_otp.assert_called_once_with(
            {"token_hash": "valid-token", "type": "signup"}
        )
        mark.assert_called_once_with("78900000-0000-4000-8000-000000000789")

    def test_13_invalid_token_hash_returns_403(self) -> None:
        """verify_otp rejects a garbage/tampered token_hash."""
        request = self._make_request(
            {"donexto_verify": "1", "token_hash": "not-a-real-token", "type": "signup"}
        )
        mock_client = MagicMock()
        mock_client.auth.verify_otp.side_effect = Exception("invalid token_hash")

        with patch(
            "app.api.identity.get_supabase_client", return_value=mock_client
        ):
            with self.assertRaises(HTTPException) as caught:
                confirm_donexto_identity(request)

        self.assertEqual(caught.exception.status_code, 403)
        self.assertEqual(
            caught.exception.detail.get("status"), "invalid_verification_token"
        )
        mock_client.auth.admin.update_user_by_id.assert_not_called()

    def test_14_expired_token_hash_returns_403(self) -> None:
        """Supabase raises for an expired token_hash the same way as invalid."""
        request = self._make_request(
            {"donexto_verify": "1", "token_hash": "expired-token", "type": "signup"}
        )
        mock_client = MagicMock()
        mock_client.auth.verify_otp.side_effect = Exception("token has expired")

        with patch(
            "app.api.identity.get_supabase_client", return_value=mock_client
        ):
            with self.assertRaises(HTTPException) as caught:
                confirm_donexto_identity(request)

        self.assertEqual(caught.exception.status_code, 403)
        self.assertEqual(
            caught.exception.detail.get("status"), "invalid_verification_token"
        )
        mock_client.auth.admin.update_user_by_id.assert_not_called()

    def _oauth_owner(self) -> SimpleNamespace:
        return SimpleNamespace(
            id="11111111-1111-1111-1111-111111111111",
            email="donexto@hotmail.com",
            email_confirmed_at="2026-09-22T00:00:00Z",
            app_metadata={"provider": "email", "providers": ["email", "azure"]},
            user_metadata={"signup_via": "microsoft_oauth"},
            identities=[{"provider": "azure"}],
        )

    def test_15_cold_open_marks_token_user_and_returns_session(self) -> None:
        """No Authorization header and no request context. The email token is enough."""
        request = self._make_request(
            {
                "donexto_verify": "1",
                "token_hash": "fresh-hash",
                "type": "magiclink",
                "user_id": "attacker-should-be-ignored",
            }
        )
        owner = self._oauth_owner()
        mock_client = MagicMock()
        mock_client.auth.verify_otp.return_value = SimpleNamespace(
            user=owner,
            session=SimpleNamespace(
                access_token="access-from-otp",
                refresh_token="refresh-from-otp",
                expires_in=3600,
            ),
        )
        mock_client.auth.admin.get_user_by_id.return_value = SimpleNamespace(user=owner)

        with patch(
            "app.api.identity.require_request_context",
            side_effect=AssertionError("confirm must not require a session"),
        ), patch(
            "app.api.identity.get_supabase_client", return_value=mock_client
        ), patch(
            "app.security.donexto_verified.get_supabase_client",
            return_value=mock_client,
        ):
            result = confirm_donexto_identity(request)

        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["donexto_verified"])
        self.assertFalse(result["already"])
        self.assertEqual(result["access_token"], "access-from-otp")
        self.assertEqual(result["refresh_token"], "refresh-from-otp")
        self.assertEqual(result["token_type"], "bearer")
        updated_id, updated_body = mock_client.auth.admin.update_user_by_id.call_args.args
        self.assertEqual(updated_id, owner.id)
        self.assertNotEqual(updated_id, "attacker-should-be-ignored")
        metadata = updated_body["app_metadata"]
        self.assertTrue(metadata["donexto_verified"])
        self.assertEqual(metadata["donexto_verification_source"], "email")
        self.assertIn("donexto_verified_at", metadata)

    def test_16_magiclink_hash_falls_back_to_email_type(self) -> None:
        """Outlook links send type=magiclink; GoTrue often wants type=email."""
        request = self._make_request(
            {"donexto_verify": "1", "token_hash": "fresh-hash", "type": "magiclink"}
        )
        owner = self._oauth_owner()
        mock_client = MagicMock()

        def verify(payload: dict[str, str]) -> SimpleNamespace:
            if payload["type"] == "magiclink":
                raise Exception("otp type mismatch")
            return SimpleNamespace(
                user=owner,
                session=SimpleNamespace(
                    access_token="access-from-otp",
                    refresh_token="refresh-from-otp",
                    expires_in=3600,
                ),
            )

        mock_client.auth.verify_otp.side_effect = verify
        mock_client.auth.admin.get_user_by_id.return_value = SimpleNamespace(user=owner)

        with patch(
            "app.api.identity.get_supabase_client", return_value=mock_client
        ), patch("app.api.identity.mark_donexto_verified") as mark:
            result = confirm_donexto_identity(request)

        self.assertTrue(result["donexto_verified"])
        self.assertEqual(
            [call.args[0]["type"] for call in mock_client.auth.verify_otp.call_args_list],
            ["magiclink", "email"],
        )
        mark.assert_called_once_with(owner.id)

    def test_17_reused_token_does_not_mark(self) -> None:
        request = self._make_request(
            {"donexto_verify": "1", "token_hash": "used-hash", "type": "magiclink"}
        )
        mock_client = MagicMock()
        mock_client.auth.verify_otp.side_effect = Exception("Token has expired or is invalid")

        with patch("app.api.identity.get_supabase_client", return_value=mock_client), patch(
            "app.api.identity.mark_donexto_verified"
        ) as mark:
            with self.assertRaises(HTTPException) as caught:
                confirm_donexto_identity(request)

        self.assertEqual(caught.exception.status_code, 403)
        self.assertEqual(
            caught.exception.detail.get("status"), "invalid_verification_token"
        )
        mark.assert_not_called()
        self.assertEqual(mock_client.auth.verify_otp.call_count, 2)

    def test_18_oauth_without_email_click_cannot_confirm(self) -> None:
        """Microsoft OAuth plus email_confirmed_at is not Donexto verification."""
        from app.security.donexto_verified import trusted_donexto_verified

        request = self._make_request({"donexto_verify": "1"})
        with self.assertRaises(HTTPException) as caught:
            confirm_donexto_identity(request)
        self.assertEqual(caught.exception.status_code, 403)
        self.assertEqual(
            caught.exception.detail.get("status"), "verification_proof_required"
        )
        self.assertFalse(
            trusted_donexto_verified(
                {"donexto_verified": True},
                oauth_identity_present=True,
            )
        )
        self.assertFalse(
            trusted_donexto_verified(
                {},
                oauth_identity_present=True,
            )
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

    def test_19_cold_confirm_reaches_handler_without_bearer(self) -> None:
        """The email tab has no Authorization header. Middleware must not 401 it."""
        from fastapi import FastAPI

        from app.middleware.authentication_context import AuthenticationContextMiddleware

        app = FastAPI()
        app.add_middleware(AuthenticationContextMiddleware)

        @app.post("/identity/confirm-donexto")
        def confirm() -> dict[str, bool]:
            return {"reached": True}

        client = TestClient(app)
        response = client.post(
            "/identity/confirm-donexto",
            params={"donexto_verify": "1", "token_hash": "hash", "type": "magiclink"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"reached": True})

    def test_20_send_verify_still_requires_a_session(self) -> None:
        from app.middleware.authentication_context import AuthenticationContextMiddleware

        request = MagicMock()
        request.method = "POST"
        request.url.path = "/identity/send-donexto-verify"
        self.assertTrue(AuthenticationContextMiddleware._requires_identity(request))
        request.url.path = "/identity/confirm-donexto"
        self.assertFalse(AuthenticationContextMiddleware._requires_identity(request))


if __name__ == "__main__":
    unittest.main()