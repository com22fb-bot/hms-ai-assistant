import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

from fastapi import HTTPException

from app.api.identity import (
    DonextoVerificationEmailRequest,
    _append_verify_flag,
    send_donexto_verification_email,
)
from app.services.donexto_verification_email import (
    _resolve_link_type,
    action_link_from_generate_response,
    build_verification_email,
    normalize_language,
    send_verification_email,
)


class DonextoVerificationEmailTests(unittest.TestCase):
    def test_localized_templates(self) -> None:
        for language, subject in {
            "es": "Confirma tu correo de Donexto",
            "en": "Confirm your Donexto email",
            "fr": "Confirmez votre e-mail Donexto",
            "it": "Conferma la tua email Donexto",
            "pt": "Confirme o seu e-mail Donexto",
        }.items():
            message = build_verification_email(language, "https://example.test/link")
            self.assertEqual(message.subject, subject)
            self.assertIn("https://example.test/link", message.body)

    def test_language_normalization_and_fallback(self) -> None:
        self.assertEqual(normalize_language("es-ES"), "es")
        self.assertEqual(normalize_language("pt_BR"), "pt")
        self.assertEqual(normalize_language("de"), "es")

    def test_extracts_action_link_from_supabase_response(self) -> None:
        response = SimpleNamespace(properties={"action_link": " https://example.test/action "})
        self.assertEqual(action_link_from_generate_response(response), "https://example.test/action")

    def test_resolve_link_type_for_existing_users(self) -> None:
        client = MagicMock()
        client.auth.admin.list_users.return_value = SimpleNamespace(
            users=[SimpleNamespace(email="pending@example.test", email_confirmed_at=None)]
        )
        self.assertEqual(_resolve_link_type(client, "pending@example.test"), "signup")
        client.auth.admin.list_users.return_value = SimpleNamespace(
            users=[SimpleNamespace(email="confirmed@example.test", email_confirmed_at="now")]
        )
        self.assertEqual(_resolve_link_type(client, "confirmed@example.test"), "magiclink")

    def test_resend_unknown_user_is_noop(self) -> None:
        client = MagicMock()
        client.auth.admin.list_users.return_value = SimpleNamespace(users=[])
        result = send_verification_email(
            client=client,
            email="unknown@example.test",
            language="es",
            redirect_to="https://app.example.test/?donexto_verify=1",
        )
        self.assertIsNone(result)
        client.auth.resend.assert_not_called()
        client.auth.admin.generate_link.assert_not_called()

    def test_resend_uses_supabase_auth_not_private_smtp(self) -> None:
        client = MagicMock()
        client.auth.admin.list_users.return_value = SimpleNamespace(
            users=[SimpleNamespace(email="user@example.test", email_confirmed_at=None)]
        )
        message = send_verification_email(
            client=client,
            email="user@example.test",
            language="en",
            redirect_to="https://app.example.test/?donexto_verify=1",
        )
        self.assertEqual(message.subject, "Confirm your Donexto email")
        client.auth.resend.assert_called_once_with(
            {
                "type": "signup",
                "email": "user@example.test",
                "options": {"email_redirect_to": "https://app.example.test/?donexto_verify=1"},
            }
        )

    def test_endpoint_requires_session_without_email_payload(self) -> None:
        with patch("app.api.identity.require_request_context", side_effect=HTTPException(status_code=401)):
            with self.assertRaises(HTTPException) as caught:
                send_donexto_verification_email(
                    DonextoVerificationEmailRequest.model_validate({"email": "attacker@example.test"})
                )
        self.assertEqual(caught.exception.status_code, 401)
        self.assertFalse(hasattr(DonextoVerificationEmailRequest(), "email"))

    def test_endpoint_returns_same_generic_body_for_existing_and_missing(self) -> None:
        context = SimpleNamespace(user=SimpleNamespace(email="user@example.test", raw_user_metadata={}))
        missing_client = MagicMock()
        missing_client.auth.admin.list_users.return_value = SimpleNamespace(users=[])
        existing_client = MagicMock()
        existing_client.auth.admin.list_users.return_value = SimpleNamespace(
            users=[SimpleNamespace(email="user@example.test", email_confirmed_at=None)]
        )
        with patch("app.api.identity.require_request_context", return_value=context), patch(
            "app.api.identity.get_supabase_client", return_value=missing_client
        ):
            missing = send_donexto_verification_email(DonextoVerificationEmailRequest())
        with patch("app.api.identity.require_request_context", return_value=context), patch(
            "app.api.identity.get_supabase_client", return_value=existing_client
        ):
            existing = send_donexto_verification_email(DonextoVerificationEmailRequest())
        self.assertEqual(missing, {"status": "sent"})
        self.assertEqual(existing, {"status": "sent"})


class AppendVerifyFlagTests(unittest.TestCase):
    def test_appends_flag_and_preserves_query(self) -> None:
        result = _append_verify_flag("https://app.donexto.com/?lang=es")
        self.assertEqual(parse_qs(urlparse(result).query), {"lang": ["es"], "donexto_verify": ["1"]})

    def test_overwrites_stale_flag_without_double_question_mark(self) -> None:
        result = _append_verify_flag("https://app.donexto.com/?donexto_verify=0")
        self.assertEqual(parse_qs(urlparse(result).query), {"donexto_verify": ["1"]})
        self.assertEqual(result.count("?"), 1)


if __name__ == "__main__":
    unittest.main()
