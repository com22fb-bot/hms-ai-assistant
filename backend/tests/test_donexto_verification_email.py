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
    VerificationEmailUserNotFound,
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

    def test_resend_unknown_user_raises_not_found(self) -> None:
        client = MagicMock()
        client.auth.admin.list_users.return_value = SimpleNamespace(users=[])
        with self.assertRaises(VerificationEmailUserNotFound):
            send_verification_email(
                client=client,
                email="unknown@example.test",
                language="es",
                redirect_to="https://app.example.test/?donexto_verify=1",
            )
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
        context = SimpleNamespace(user=SimpleNamespace(id="user-1", email="user@example.test", raw_user_metadata={}))
        missing_client = MagicMock()
        missing_client.auth.admin.list_users.return_value = SimpleNamespace(users=[])
        existing_client = MagicMock()
        existing_client.auth.admin.list_users.return_value = SimpleNamespace(
            users=[SimpleNamespace(email="user@example.test", email_confirmed_at=None)]
        )
        with patch("app.api.identity.require_request_context", return_value=context), patch(
            "app.api.identity.get_supabase_client", return_value=missing_client
        ), self.assertLogs("app.api.identity", level="INFO") as missing_logs:
            missing = send_donexto_verification_email(DonextoVerificationEmailRequest())
        with patch("app.api.identity.require_request_context", return_value=context), patch(
            "app.api.identity.get_supabase_client", return_value=existing_client
        ):
            existing = send_donexto_verification_email(DonextoVerificationEmailRequest())
        self.assertEqual(missing, {"status": "sent"})
        self.assertEqual(existing, {"status": "sent"})
        self.assertTrue(
            any("donexto_verify_resend_unknown_user" in record for record in missing_logs.output)
        )
        existing_client.auth.resend.assert_called_once()

    def test_endpoint_logs_provider_error_but_returns_generic_body(self) -> None:
        context = SimpleNamespace(user=SimpleNamespace(id="user-1", email="user@example.test", raw_user_metadata={}))
        failing_client = MagicMock()
        failing_client.auth.admin.list_users.side_effect = RuntimeError("supabase down")
        with patch("app.api.identity.require_request_context", return_value=context), patch(
            "app.api.identity.get_supabase_client", return_value=failing_client
        ), self.assertLogs("app.api.identity", level="ERROR") as error_logs:
            result = send_donexto_verification_email(DonextoVerificationEmailRequest())
        self.assertEqual(result, {"status": "sent"})
        self.assertTrue(
            any("donexto_verify_resend_provider_error" in record for record in error_logs.output)
        )


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
