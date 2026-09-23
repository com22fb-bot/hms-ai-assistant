import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault(
    "OAUTH_ENCRYPTION_KEY",
    "test-oauth-encryption-key-32chars!!",
)

from fastapi import HTTPException

from app.api.admin_ops import admin_delete_user, deletion_block_reason
from app.middleware.authentication_context import AuthenticationContextMiddleware


class _FakeRequest:
    def __init__(self, path: str, method: str = "GET") -> None:
        self.method = method
        self.url = SimpleNamespace(path=path)
        self.client = SimpleNamespace(host="127.0.0.1")
        self.headers = {}


class AdminDeleteGuardTests(unittest.TestCase):
    def test_admin_routes_require_a_session(self) -> None:
        request = _FakeRequest("/admin/users")
        self.assertTrue(AuthenticationContextMiddleware._requires_identity(request))

    def test_cannot_delete_self_or_allowlist(self) -> None:
        allow = {"hmcelinfo@gmail.com", "donexto@hotmail.com"}
        self.assertIn(
            "propia",
            deletion_block_reason(
                actor_id="admin-1",
                target_id="admin-1",
                target_email="hmcelinfo@gmail.com",
                allowlist=allow,
            )
            or "",
        )
        self.assertIn(
            "ADMIN_EMAILS",
            deletion_block_reason(
                actor_id="admin-1",
                target_id="other-1",
                target_email="donexto@hotmail.com",
                allowlist=allow,
            )
            or "",
        )
        self.assertIsNone(
            deletion_block_reason(
                actor_id="admin-1",
                target_id="test-1",
                target_email="prueba@hotmail.com",
                allowlist=allow,
            )
        )

    def test_delete_removes_auth_user_and_workspace(self) -> None:
        client = MagicMock()
        client.auth.admin.get_user_by_id.return_value = SimpleNamespace(
            user=SimpleNamespace(id="test-1", email="prueba@hotmail.com")
        )
        context = SimpleNamespace(
            user=SimpleNamespace(id="admin-1", email="hmcelinfo@gmail.com")
        )
        with (
            patch.dict(os.environ, {"ADMIN_EMAILS": "hmcelinfo@gmail.com"}),
            patch("app.api.admin_ops.require_request_context", return_value=context),
            patch("app.api.admin_ops.get_supabase_client", return_value=client),
        ):
            result = admin_delete_user("test-1")
        self.assertEqual(result["status"], "deleted")
        self.assertEqual(result["email"], "prueba@hotmail.com")
        client.auth.admin.delete_user.assert_called_once_with("test-1")
        client.table.assert_any_call("workspace_members")
        client.table.assert_any_call("profiles")

    def test_delete_refuses_admin_allowlist_email(self) -> None:
        client = MagicMock()
        client.auth.admin.get_user_by_id.return_value = SimpleNamespace(
            user=SimpleNamespace(id="other-admin", email="donexto@hotmail.com")
        )
        context = SimpleNamespace(
            user=SimpleNamespace(id="admin-1", email="hmcelinfo@gmail.com")
        )
        with (
            patch.dict(
                os.environ,
                {"ADMIN_EMAILS": "hmcelinfo@gmail.com,donexto@hotmail.com"},
            ),
            patch("app.api.admin_ops.require_request_context", return_value=context),
            patch("app.api.admin_ops.get_supabase_client", return_value=client),
        ):
            with self.assertRaises(HTTPException) as caught:
                admin_delete_user("other-admin")
        self.assertEqual(caught.exception.status_code, 403)
        client.auth.admin.delete_user.assert_not_called()


if __name__ == "__main__":
    unittest.main()
