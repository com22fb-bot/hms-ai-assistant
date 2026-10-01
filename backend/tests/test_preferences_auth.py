import os
import unittest

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault(
    "OAUTH_ENCRYPTION_KEY",
    "test-oauth-encryption-key-32chars!!",
)

from app.middleware.authentication_context import AuthenticationContextMiddleware


class _FakeRequest:
    def __init__(self, path: str, method: str = "GET") -> None:
        self.method = method
        self.url = type("U", (), {"path": path})()


class PreferencesAuthTests(unittest.TestCase):
    def test_preferences_require_identity(self) -> None:
        for method in ("GET", "PUT"):
            request = _FakeRequest("/preferences", method)
            self.assertTrue(
                AuthenticationContextMiddleware._requires_identity(request),
                method,
            )

    def test_push_routes_require_identity(self) -> None:
        for path in (
            "/push/vapid-public-key",
            "/push/subscriptions",
            "/push/subscriptions/deactivate",
            "/push/test",
            "/push/status",
            "/push/notifications",
        ):
            request = _FakeRequest(path, "POST")
            self.assertTrue(
                AuthenticationContextMiddleware._requires_identity(request),
                path,
            )

    def test_options_and_unrelated_paths_stay_open(self) -> None:
        self.assertFalse(
            AuthenticationContextMiddleware._requires_identity(
                _FakeRequest("/preferences", "OPTIONS")
            )
        )
        self.assertFalse(
            AuthenticationContextMiddleware._requires_identity(
                _FakeRequest("/health")
            )
        )
