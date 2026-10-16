"""Google callback: nunca JSON crudo; estado se borra después del canje."""

import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault("OAUTH_ENCRYPTION_KEY", "test-oauth-encryption-key-32chars!!")

from fastapi.responses import RedirectResponse

from app.api import auth
from app.services.oauth_storage import OAuthStateError

GMAIL = "https://www.googleapis.com/auth/gmail.readonly"


def _request(**params: str) -> SimpleNamespace:
    return SimpleNamespace(query_params=params, headers={}, url=SimpleNamespace(query=""))


class GoogleCallbackFriendlyTests(unittest.TestCase):
    def _location(self, response: object) -> str:
        self.assertIsInstance(response, RedirectResponse)
        self.assertEqual(response.status_code, 302)  # type: ignore[attr-defined]
        return str(response.headers["location"])  # type: ignore[attr-defined]

    def test_used_state_redirects_with_reason(self) -> None:
        with patch.object(auth, "oauth_storage") as storage:
            storage.load_oauth_state.side_effect = OAuthStateError("ya fue utilizado")
            response = auth.google_callback(_request(state="gmail.x.y", code="c"))  # type: ignore[arg-type]
        location = self._location(response)
        self.assertTrue(location.startswith("http"))
        self.assertNotIn("api.donexto.com", location)
        self.assertIn("donexto=oauth_error", location)
        self.assertIn("reason=state_invalid", location)
        self.assertNotIn("technical_detail", location)
        storage.consume_oauth_state.assert_not_called()

    def test_missing_state_and_google_error_redirect(self) -> None:
        self.assertIn("reason=state_invalid", self._location(auth.google_callback(_request(code="c"))))  # type: ignore[arg-type]
        self.assertIn(
            "reason=access_denied",
            self._location(auth.google_callback(_request(error="access_denied"))),  # type: ignore[arg-type]
        )

    def test_unchecked_gmail_permission_is_explained(self) -> None:
        with patch.object(auth, "oauth_storage") as storage, patch.object(auth, "create_google_flow") as flow:
            storage.load_oauth_state.return_value = {"return_to": ""}
            response = auth.google_callback(  # type: ignore[arg-type]
                _request(state="gmail.x.y", code="c", scope="email profile openid")
            )
        self.assertIn("reason=gmail_permission_missing", self._location(response))
        flow.assert_not_called()
        storage.delete_oauth_state.assert_called_once_with("gmail.x.y")

    def test_token_failure_redirects_and_burns_state_once(self) -> None:
        fake_flow = MagicMock()
        fake_flow.fetch_token.side_effect = RuntimeError("invalid_grant")
        with patch.object(auth, "oauth_storage") as storage, patch.object(
            auth, "create_google_flow", return_value=fake_flow
        ), patch.object(auth, "_public_request_url", return_value="https://x"):
            storage.load_oauth_state.return_value = {"return_to": ""}
            response = auth.google_callback(  # type: ignore[arg-type]
                _request(state="gmail.x.y", code="c", scope=f"email {GMAIL}")
            )
        self.assertIn("reason=token_failed", self._location(response))
        storage.delete_oauth_state.assert_called_once_with("gmail.x.y")
        storage.consume_oauth_state.assert_not_called()


if __name__ == "__main__":
    unittest.main()
