import os
import unittest

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault(
    "OAUTH_ENCRYPTION_KEY",
    "test-oauth-encryption-key-32chars!!",
)

from app.services.microsoft_oauth import microsoft_tenant_from_state
from app.services.oauth_storage import OAuthStorage
from app.services.yahoo_oauth import (
    encode_login_hint_in_state_prefix,
    login_hint_from_oauth_state,
    oauth_email_mismatch_message,
    oauth_identity_block_message,
    yahoo_intent_from_state,
)


class _Result:
    def __init__(self, data: list[dict[str, str]]) -> None:
        self.data = data


class _Table:
    def delete(self) -> "_Table":
        return self

    def lt(self, *_args: object, **_kwargs: object) -> "_Table":
        return self

    def insert(self, _payload: dict[str, object]) -> "_Table":
        return self

    def execute(self) -> _Result:
        return _Result([{"ok": "1"}])


class _Client:
    def table(self, _name: str) -> _Table:
        return _Table()


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

    def test_lowercasing_the_prefix_destroys_the_hint(self) -> None:
        """`.lower()` on the whole prefix is the bug: @ forces uppercase base64."""
        prefix = encode_login_hint_in_state_prefix(
            "login.consumers",
            "hector@hotmail.com",
        )
        encoded = prefix.rsplit(".", 1)[-1]
        self.assertNotEqual(encoded, encoded.lower())
        self.assertIsNone(
            login_hint_from_oauth_state(f"{prefix.lower()}.token")
        )

    def _issued_state(self, state_prefix: str, provider: str) -> str:
        storage = OAuthStorage(client=_Client())
        return storage.create_oauth_state(
            provider=provider,
            ttl_minutes=15,
            return_to="https://app.donexto.com/",
            state_prefix=state_prefix,
        )

    def test_create_oauth_state_roundtrip_microsoft_hint(self) -> None:
        prefix = encode_login_hint_in_state_prefix(
            "Login.Consumers",
            "Hector@Hotmail.com",
        )
        state = self._issued_state(prefix, "microsoft")
        recovered = login_hint_from_oauth_state(state)
        self.assertEqual(recovered, "hector@hotmail.com")
        self.assertTrue(state.startswith("login.consumers.h."))
        self.assertEqual(yahoo_intent_from_state(state), "login")
        self.assertEqual(microsoft_tenant_from_state(state), "consumers")
        self.assertIsNone(
            oauth_identity_block_message(
                recovered,
                "HECTOR@hotmail.com",
                provider_label="Microsoft",
            )
        )
        mismatch = oauth_identity_block_message(
            recovered,
            "otra@outlook.com",
            provider_label="Microsoft",
        )
        self.assertIn("Firmaste con otra@outlook.com", mismatch or "")
        self.assertIn("hector@hotmail.com", mismatch or "")

    def test_create_oauth_state_roundtrip_yahoo_hint(self) -> None:
        prefix = encode_login_hint_in_state_prefix(
            "Signup",
            "Hsalcidor@Yahoo.com",
        )
        state = self._issued_state(prefix, "yahoo")
        recovered = login_hint_from_oauth_state(state)
        self.assertEqual(recovered, "hsalcidor@yahoo.com")
        self.assertTrue(state.startswith("signup.h."))
        self.assertEqual(yahoo_intent_from_state(state), "signup")
        self.assertIsNone(
            oauth_identity_block_message(
                recovered,
                "hsalcidor@yahoo.com",
                provider_label="Yahoo",
            )
        )

    def test_create_oauth_state_without_hint_stays_fail_closed(self) -> None:
        state = self._issued_state("Login.Consumers", "microsoft")
        self.assertTrue(state.startswith("login.consumers."))
        self.assertIsNone(login_hint_from_oauth_state(state))
        message = oauth_identity_block_message(
            login_hint_from_oauth_state(state),
            "hector@hotmail.com",
            provider_label="Microsoft",
        )
        self.assertIn("no recibió el correo", message or "")
        self.assertNotIn("Firmaste con", message or "")


if __name__ == "__main__":
    unittest.main()
