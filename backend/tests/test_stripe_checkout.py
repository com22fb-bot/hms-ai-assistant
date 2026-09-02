import os
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault(
    "OAUTH_ENCRYPTION_KEY",
    "test-oauth-encryption-key-32chars!!",
)

from fastapi import HTTPException

from app.middleware.authentication_context import AuthenticationContextMiddleware
from app.services.stripe_checkout import (
    create_checkout_session,
    missing_stripe_message,
    plan_payload,
)


class _FakeRequest:
    def __init__(self, path: str) -> None:
        self.method = "POST"
        self.url = type("U", (), {"path": path})()
        self.client = type("C", (), {"host": "127.0.0.1"})()
        self.headers = {}


class StripeCheckoutTests(unittest.TestCase):
    def test_billing_requires_identity(self) -> None:
        request = _FakeRequest("/billing/checkout")
        self.assertTrue(
            AuthenticationContextMiddleware._requires_identity(request)
        )

    def test_plan_without_keys_is_not_configured(self) -> None:
        with patch.dict(os.environ, {"STRIPE_SECRET_KEY": "", "STRIPE_PRICE_NORMAL_MONTHLY": ""}, clear=False):
            payload = plan_payload()
        self.assertEqual(payload["status"], "not_configured")
        self.assertFalse(payload["checkout_ready"])
        self.assertIn("STRIPE_SECRET_KEY", str(payload["message"]))

    def test_live_key_is_rejected(self) -> None:
        with patch.dict(
            os.environ,
            {
                "STRIPE_SECRET_KEY": "sk_live_not_allowed",
                "STRIPE_PRICE_NORMAL_MONTHLY": "price_123",
            },
            clear=False,
        ):
            self.assertIn("sk_test_", missing_stripe_message())

    def test_checkout_without_key_returns_503_message(self) -> None:
        with patch.dict(os.environ, {"STRIPE_SECRET_KEY": ""}, clear=False):
            with self.assertRaises(HTTPException) as caught:
                create_checkout_session(
                    customer_email="ana@hotmail.com",
                    client_reference_id="user-1",
                )
        self.assertEqual(caught.exception.status_code, 503)
        self.assertIn(
            "STRIPE_SECRET_KEY",
            caught.exception.detail["message"],
        )

    def test_checkout_with_test_key_posts_to_stripe(self) -> None:
        response = MagicMock()
        response.status_code = 200
        response.content = b"{}"
        response.json.return_value = {
            "id": "cs_test_1",
            "url": "https://checkout.stripe.com/c/pay/cs_test_1",
        }
        with (
            patch.dict(
                os.environ,
                {
                    "STRIPE_SECRET_KEY": "sk_test_abc",
                    "STRIPE_PRICE_NORMAL_MONTHLY": "price_normal_test",
                },
                clear=False,
            ),
            patch("app.services.stripe_checkout.httpx.post", return_value=response) as post,
        ):
            result = create_checkout_session(
                customer_email="ana@hotmail.com",
                client_reference_id="user-1",
            )
        self.assertEqual(result["checkout_url"], "https://checkout.stripe.com/c/pay/cs_test_1")
        self.assertTrue(result["test_mode"])
        post.assert_called_once()
        self.assertIn("sk_test_abc", post.call_args.kwargs["headers"]["Authorization"])


if __name__ == "__main__":
    unittest.main()
