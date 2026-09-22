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
        client.auth.admin.get_user_by_email.side_effect = RuntimeError("missing")
        with self.assertRaises(VerificationEmailUserNotFound):
            send_verification_email(
                client=client,
                email="unknown@example.test",
                language="es",
                redirect_to="https://app.example.test/?donexto_verify=1",
            )
        client.auth.resend.assert_not_called()
        client.auth.admin.generate_link.assert_not_called()

    def test_send_uses_localized_smtp_not_auth_resend(self) -> None:
        client = MagicMock()
        client.auth.admin.get_user_by_email.side_effect = RuntimeError("missing")
        client.auth.admin.list_users.return_value = SimpleNamespace(
            users=[SimpleNamespace(id="user-1", email="user@example.test", email_confirmed_at=None)]
        )
        client.auth.admin.generate_link.return_value = SimpleNamespace(
            properties={
                "hashed_token": "hash-token",
                "verification_type": "magiclink",
            }
        )
        with patch(
            "app.services.support_notify.send_transactional_email",
            return_value=True,
        ) as deliver:
            message = send_verification_email(
                client=client,
                email="user@example.test",
                language="en",
                redirect_to="https://app.example.test/?donexto_verify=1",
            )
        self.assertEqual(message.subject, "Confirm your Donexto email")
        self.assertIn("hash-token", message.body)
        self.assertIn("token_hash=hash-token", message.body)
        self.assertIn("type=magiclink", message.body)
        self.assertNotIn("type=signup", message.body)
        self.assertEqual(
            client.auth.admin.generate_link.call_args.args[0]["type"],
            "magiclink",
        )
        client.auth.resend.assert_not_called()
        deliver.assert_called_once()
        self.assertEqual(deliver.call_args.args[0], "user@example.test")
        self.assertEqual(deliver.call_args.args[1], "Confirm your Donexto email")
        self.assertIn("hash-token", deliver.call_args.args[2])

    def test_lookup_finds_user_past_first_page(self) -> None:
        client = MagicMock()
        client.auth.admin.get_user_by_email.side_effect = RuntimeError("missing")

        def list_users(page: int = 1, per_page: int = 200):
            if page == 1:
                return SimpleNamespace(
                    users=[
                        SimpleNamespace(id=f"other-{index}", email=f"other{index}@example.test")
                        for index in range(per_page)
                    ]
                )
            if page == 2:
                return SimpleNamespace(
                    users=[
                        SimpleNamespace(
                            id="user-9",
                            email="user@example.test",
                            email_confirmed_at="2026-09-01T00:00:00Z",
                        )
                    ]
                )
            return SimpleNamespace(users=[])

        client.auth.admin.list_users.side_effect = list_users
        client.auth.admin.generate_link.return_value = SimpleNamespace(
            properties={"hashed_token": "page-two", "verification_type": "magiclink"}
        )
        with patch(
            "app.services.support_notify.send_transactional_email",
            return_value=True,
        ):
            message = send_verification_email(
                client=client,
                email="user@example.test",
                language="es",
                redirect_to="https://app.donexto.com/?donexto_verify=1",
            )
        self.assertIn("Confirma tu correo de Donexto", message.subject)
        self.assertIn("type=magiclink", message.body)
        client.auth.resend.assert_not_called()
        client.auth.admin.generate_link.assert_called_once()

    def test_microsoft_oauth_without_confirmed_at_stays_on_magiclink(self) -> None:
        """Signup resend is a no-op for provider-confirmed OAuth users."""
        client = MagicMock()
        client.auth.admin.get_user_by_id.return_value = SimpleNamespace(
            user=SimpleNamespace(
                id="ms-user",
                email="donexto@hotmail.com",
                email_confirmed_at=None,
                user_metadata={"signup_via": "microsoft_oauth"},
            )
        )
        client.auth.admin.generate_link.return_value = SimpleNamespace(
            properties={"hashed_token": "ms-token", "verification_type": "magiclink"}
        )
        with patch(
            "app.services.support_notify.send_transactional_email",
            return_value=True,
        ):
            message = send_verification_email(
                client=client,
                email="donexto@hotmail.com",
                language="es",
                redirect_to="https://app.donexto.com/?donexto_verify=1",
                user_id="ms-user",
            )
        self.assertIn("type=magiclink", message.body)
        self.assertNotIn("type=signup", message.body)
        self.assertEqual(
            client.auth.admin.generate_link.call_args.args[0]["type"],
            "magiclink",
        )
        client.auth.resend.assert_not_called()
        client.auth.sign_in_with_otp.assert_not_called()

    def test_user_id_lookup_ignores_empty_first_page(self) -> None:
        client = MagicMock()
        client.auth.admin.list_users.return_value = SimpleNamespace(users=[])
        client.auth.admin.get_user_by_id.return_value = SimpleNamespace(
            user=SimpleNamespace(
                id="user-1",
                email="user@example.test",
                email_confirmed_at="2026-09-01T00:00:00Z",
            )
        )
        client.auth.admin.generate_link.return_value = SimpleNamespace(
            properties={"hashed_token": "by-id", "verification_type": "magiclink"}
        )
        with patch(
            "app.services.support_notify.send_transactional_email",
            return_value=True,
        ):
            send_verification_email(
                client=client,
                email="user@example.test",
                language="es",
                redirect_to="https://app.donexto.com/?donexto_verify=1",
                user_id="user-1",
            )
        client.auth.admin.list_users.assert_not_called()
        client.auth.resend.assert_not_called()
        self.assertEqual(
            client.auth.admin.generate_link.call_args.args[0]["type"],
            "magiclink",
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
        missing_client.auth.admin.get_user_by_email.side_effect = RuntimeError("missing")
        existing_client = MagicMock()
        existing_client.auth.admin.get_user_by_id.return_value = SimpleNamespace(
            user=SimpleNamespace(
                id="user-1",
                email="user@example.test",
                email_confirmed_at=None,
            )
        )
        existing_client.auth.admin.generate_link.return_value = SimpleNamespace(
            properties={"hashed_token": "hash-token", "verification_type": "magiclink"}
        )
        with patch("app.api.identity.require_request_context", return_value=context), patch(
            "app.api.identity.get_supabase_client", return_value=missing_client
        ), self.assertLogs("app.api.identity", level="INFO") as missing_logs:
            missing = send_donexto_verification_email(DonextoVerificationEmailRequest())
        with patch("app.api.identity.require_request_context", return_value=context), patch(
            "app.api.identity.get_supabase_client", return_value=existing_client
        ), patch(
            "app.services.support_notify.send_transactional_email",
            return_value=True,
        ):
            existing = send_donexto_verification_email(DonextoVerificationEmailRequest())
        self.assertEqual(missing, {"status": "sent"})
        self.assertEqual(existing, {"status": "sent"})
        self.assertTrue(
            any("donexto_verify_resend_unknown_user" in record for record in missing_logs.output)
        )
        existing_client.auth.resend.assert_not_called()
        existing_client.auth.admin.generate_link.assert_called_once()
        self.assertEqual(
            existing_client.auth.admin.generate_link.call_args.args[0]["type"],
            "magiclink",
        )

    def test_endpoint_logs_provider_error_and_returns_503(self) -> None:
        context = SimpleNamespace(user=SimpleNamespace(id="user-1", email="user@example.test", raw_user_metadata={}))
        failing_client = MagicMock()
        failing_client.auth.admin.get_user_by_id.side_effect = RuntimeError("supabase down")
        failing_client.auth.admin.get_user_by_email.side_effect = RuntimeError("supabase down")
        failing_client.auth.admin.list_users.side_effect = RuntimeError("supabase down")
        with patch("app.api.identity.require_request_context", return_value=context), patch(
            "app.api.identity.get_supabase_client", return_value=failing_client
        ), self.assertLogs("app.api.identity", level="ERROR") as error_logs:
            with self.assertRaises(HTTPException) as caught:
                send_donexto_verification_email(DonextoVerificationEmailRequest())
        self.assertEqual(caught.exception.status_code, 503)
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
