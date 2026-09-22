import os
import unittest

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault(
    "OAUTH_ENCRYPTION_KEY",
    "test-oauth-encryption-key-32chars!!",
)

from app.services.yahoo_oauth import (
    encode_login_hint_in_state_prefix,
    login_hint_from_oauth_state,
    oauth_email_mismatch_message,
    oauth_identity_block_message,
)


class OAuthLoginHintTests(unittest.TestCase):
    def test_roundtrip_hint_in_state(self) -> None:
        prefix = encode_login_hint_in_state_prefix(
            "login.consumers",
            "onexto@hotmail.com",
        )
        self.assertTrue(prefix.startswith("login.consumers.h."))
        self.assertEqual(
            login_hint_from_oauth_state(f"{prefix}.random-token"),
            "onexto@hotmail.com",
        )

    def test_state_without_hint(self) -> None:
        self.assertEqual(
            encode_login_hint_in_state_prefix("signup", "not-an-email"),
            "signup",
        )
        self.assertIsNone(login_hint_from_oauth_state("signup.token"))

    def test_mismatch_message(self) -> None:
        message = oauth_email_mismatch_message(
            "hector@hotmail.com",
            "otra@outlook.com",
            provider_label="Microsoft",
        )
        self.assertIsNotNone(message)
        self.assertIn("hector@hotmail.com", message or "")
        self.assertIn("otra@outlook.com", message or "")

    def test_match_returns_none(self) -> None:
        self.assertIsNone(
            oauth_email_mismatch_message(
                "onexto@hotmail.com",
                "onexto@hotmail.com",
            )
        )

    def test_missing_hint_is_fail_closed(self) -> None:
        message = oauth_identity_block_message(
            None,
            "donexto@hotmail.com",
            provider_label="Microsoft",
        )
        self.assertIsNotNone(message)
        self.assertIn("No se abrió sesión", message or "")

    def test_mismatch_block_names_both_emails(self) -> None:
        message = oauth_identity_block_message(
            "nadie@hotmail.com",
            "donexto@hotmail.com",
            provider_label="Microsoft",
        )
        self.assertIn("nadie@hotmail.com", message or "")
        self.assertIn("donexto@hotmail.com", message or "")
        self.assertIn("No se abrió sesión", message or "")

    def test_matching_hint_is_not_blocked(self) -> None:
        self.assertIsNone(
            oauth_identity_block_message(
                "donexto@hotmail.com",
                "Donexto@Hotmail.com",
                provider_label="Microsoft",
            )
        )


if __name__ == "__main__":
    unittest.main()
