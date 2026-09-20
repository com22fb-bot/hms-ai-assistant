import os
import smtplib
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

from app.services.donexto_verification_email import (
    _resolve_link_type,
    action_link_from_generate_response,
    build_verification_email,
    normalize_language,
    send_verification_email,
)
from app.services.support_notify import SMTPDeliveryError


class DonextoVerificationEmailTests(unittest.TestCase):
    # ------------------------------------------------------------------ i18n
    def test_spanish_email(self) -> None:
        message = build_verification_email("es", "https://example.test/link")
        self.assertEqual(message.subject, "Confirma tu correo de Donexto")
        self.assertIn("Confirma tu correo", message.body)
        self.assertIn("https://example.test/link", message.body)

    def test_english_email(self) -> None:
        message = build_verification_email("en", "https://example.test/link")
        self.assertEqual(message.subject, "Confirm your Donexto email")
        self.assertIn("Confirm your Donexto email", message.body)

    def test_french_email(self) -> None:
        message = build_verification_email("fr", "https://example.test/link")
        self.assertEqual(message.subject, "Confirmez votre e-mail Donexto")
        self.assertIn("Confirmez votre e-mail Donexto", message.body)

    def test_italian_email(self) -> None:
        message = build_verification_email("it", "https://example.test/link")
        self.assertEqual(message.subject, "Conferma la tua email Donexto")
        self.assertIn("Conferma la tua email Donexto", message.body)

    def test_portuguese_email(self) -> None:
        message = build_verification_email("pt", "https://example.test/link")
        self.assertEqual(message.subject, "Confirme o seu e-mail Donexto")
        self.assertIn("Confirme o seu e-mail Donexto", message.body)

    def test_regional_tag_reduces_to_base_language(self) -> None:
        self.assertEqual(normalize_language("es-ES"), "es")
        self.assertEqual(normalize_language("pt-BR"), "pt")
        self.assertEqual(normalize_language("en_US"), "en")

    def test_unknown_language_falls_back_to_spanish(self) -> None:
        message = build_verification_email("de", "https://example.test/link")
        self.assertEqual(message.subject, "Confirma tu correo de Donexto")
        self.assertIn("Confirma tu correo", message.body)

    # -------------------------------------------- action_link extraction
    def test_extracts_action_link_from_supabase_response(self) -> None:
        response = SimpleNamespace(
            properties={"action_link": " https://example.test/action "}
        )
        self.assertEqual(
            action_link_from_generate_response(response),
            "https://example.test/action",
        )

    # -------------------------------- signup vs magiclink auto-selection
    def test_resolve_link_type_returns_signup_when_user_not_found(self) -> None:
        client = MagicMock()
        client.auth.admin.list_users.return_value = SimpleNamespace(users=[])
        self.assertEqual(
            _resolve_link_type(client, "brand-new@example.test"),
            "signup",
        )

    def test_resolve_link_type_returns_signup_for_unconfirmed_user(self) -> None:
        client = MagicMock()
        client.auth.admin.list_users.return_value = SimpleNamespace(
            users=[
                SimpleNamespace(
                    email="pending@example.test",
                    email_confirmed_at=None,
                )
            ]
        )
        self.assertEqual(
            _resolve_link_type(client, "pending@example.test"),
            "signup",
        )

    def test_resolve_link_type_returns_magiclink_for_confirmed_user(self) -> None:
        client = MagicMock()
        client.auth.admin.list_users.return_value = SimpleNamespace(
            users=[
                SimpleNamespace(
                    email="confirmed@example.test",
                    email_confirmed_at="2026-01-01T00:00:00Z",
                )
            ]
        )
        self.assertEqual(
            _resolve_link_type(client, "confirmed@example.test"),
            "magiclink",
        )

    def test_resolve_link_type_falls_back_to_signup_on_error(self) -> None:
        client = MagicMock()
        client.auth.admin.list_users.side_effect = RuntimeError("boom")
        self.assertEqual(
            _resolve_link_type(client, "anything@example.test"),
            "signup",
        )

    # ---------------------------------------------- end-to-end SMTP flow
    def test_sends_localized_email_with_supabase_action_link(self) -> None:
        client = MagicMock()
        smtp_password = "secret-that-must-not-leak"
        # Unconfirmed user → signup link type is used.
        client.auth.admin.list_users.return_value = SimpleNamespace(users=[])
        client.auth.admin.generate_link.return_value = {
            "properties": {"action_link": "https://example.test/action"}
        }
        with patch.dict(
            os.environ,
            {
                "SUPPORT_SMTP_HOST": "smtp.gmail.com",
                "SUPPORT_SMTP_PORT": "587",
                "SUPPORT_SMTP_USER": "sender@example.test",
                "SUPPORT_SMTP_PASSWORD": smtp_password,
                "SUPPORT_SMTP_FROM": "sender@example.test",
            },
        ), patch("app.services.support_notify.smtplib.SMTP") as smtp_class:
            message = send_verification_email(
                client=client,
                email="recipient@example.test",
                language="en",
                redirect_to="https://app.example.test/?donexto_verify=1",
            )

        smtp = smtp_class.return_value.__enter__.return_value
        smtp.starttls.assert_called_once_with()
        smtp.login.assert_called_once_with("sender@example.test", smtp_password)
        smtp.send_message.assert_called_once()
        sent_message = smtp.send_message.call_args.args[0]
        self.assertEqual(message.subject, "Confirm your Donexto email")
        self.assertIn("https://example.test/action", sent_message.get_content())
        client.auth.admin.generate_link.assert_called_once_with(
            {
                "type": "signup",
                "email": "recipient@example.test",
                "options": {
                    "redirect_to": "https://app.example.test/?donexto_verify=1"
                },
            }
        )

    def test_sends_via_smtp_ssl_when_port_is_465(self) -> None:
        client = MagicMock()
        client.auth.admin.list_users.return_value = SimpleNamespace(users=[])
        client.auth.admin.generate_link.return_value = {
            "properties": {"action_link": "https://example.test/action"}
        }
        with patch.dict(
            os.environ,
            {
                "SUPPORT_SMTP_HOST": "smtp.resend.com",
                "SUPPORT_SMTP_PORT": "465",
                "SUPPORT_SMTP_USER": "resend",
                "SUPPORT_SMTP_PASSWORD": "re_secret",
                "SUPPORT_SMTP_FROM": "noreply@donexto.com",
            },
        ), patch("app.services.support_notify.smtplib.SMTP_SSL") as ssl_class, \
             patch("app.services.support_notify.smtplib.SMTP") as plain_class:
            send_verification_email(
                client=client,
                email="recipient@example.test",
                language="es",
                redirect_to="https://app.example.test/?donexto_verify=1",
            )

        ssl_class.assert_called_once()
        plain_class.assert_not_called()
        ssl_smtp = ssl_class.return_value.__enter__.return_value
        ssl_smtp.login.assert_called_once_with("resend", "re_secret")
        ssl_smtp.send_message.assert_called_once()
        # No starttls on 465.
        self.assertFalse(hasattr(ssl_smtp, "starttls") and ssl_smtp.starttls.called)

    def test_smtp_authentication_error_is_safe(self) -> None:
        client = MagicMock()
        client.auth.admin.list_users.return_value = SimpleNamespace(users=[])
        smtp_password = "auth-secret-that-must-not-leak"
        client.auth.admin.generate_link.return_value = {
            "properties": {"action_link": "https://example.test/action"}
        }
        with patch.dict(
            os.environ,
            {
                "SUPPORT_SMTP_HOST": "smtp.gmail.com",
                "SUPPORT_SMTP_PORT": "587",
                "SUPPORT_SMTP_USER": "sender@example.test",
                "SUPPORT_SMTP_PASSWORD": smtp_password,
            },
        ), patch("app.services.support_notify.smtplib.SMTP") as smtp_class:
            smtp = smtp_class.return_value.__enter__.return_value
            smtp.login.side_effect = smtplib.SMTPAuthenticationError(
                535, b"authentication failed"
            )
            with self.assertRaises(SMTPDeliveryError) as caught:
                send_verification_email(
                    client=client,
                    email="recipient@example.test",
                    language="es",
                    redirect_to="https://app.example.test/?donexto_verify=1",
                )

        self.assertIn("SMTPAuthenticationError", str(caught.exception))
        self.assertIn("smtp.gmail.com:587", str(caught.exception))
        self.assertNotIn(smtp_password, str(caught.exception))

    def test_smtp_connection_error_is_safe(self) -> None:
        client = MagicMock()
        client.auth.admin.list_users.return_value = SimpleNamespace(users=[])
        smtp_password = "connection-secret-that-must-not-leak"
        client.auth.admin.generate_link.return_value = {
            "properties": {"action_link": "https://example.test/action"}
        }
        with patch.dict(
            os.environ,
            {
                "SUPPORT_SMTP_HOST": "smtp.gmail.com",
                "SUPPORT_SMTP_PORT": "587",
                "SUPPORT_SMTP_USER": "sender@example.test",
                "SUPPORT_SMTP_PASSWORD": smtp_password,
            },
        ), patch(
            "app.services.support_notify.smtplib.SMTP",
            side_effect=OSError("connection refused"),
        ):
            with self.assertRaises(SMTPDeliveryError) as caught:
                send_verification_email(
                    client=client,
                    email="recipient@example.test",
                    language="es",
                    redirect_to="https://app.example.test/?donexto_verify=1",
                )

        self.assertIn("OSError", str(caught.exception))
        self.assertIn("smtp.gmail.com:587", str(caught.exception))
        self.assertNotIn(smtp_password, str(caught.exception))


class AppendVerifyFlagTests(unittest.TestCase):
    """Tests for the identity._append_verify_flag helper (fix 3)."""

    def _run(self, url: str) -> str:
        from app.api.identity import _append_verify_flag
        return _append_verify_flag(url)

    def test_appends_flag_on_clean_url(self) -> None:
        out = self._run("https://app.donexto.com/")
        parsed = urlparse(out)
        self.assertEqual(parse_qs(parsed.query), {"donexto_verify": ["1"]})

    def test_preserves_existing_query_params(self) -> None:
        out = self._run("https://app.donexto.com/?lang=es&ref=welcome")
        parsed = urlparse(out)
        q = parse_qs(parsed.query)
        self.assertEqual(q["lang"], ["es"])
        self.assertEqual(q["ref"], ["welcome"])
        self.assertEqual(q["donexto_verify"], ["1"])

    def test_overwrites_stale_flag(self) -> None:
        out = self._run("https://app.donexto.com/?donexto_verify=0")
        parsed = urlparse(out)
        self.assertEqual(parse_qs(parsed.query), {"donexto_verify": ["1"]})

    def test_never_produces_double_question_mark(self) -> None:
        out = self._run("https://app.donexto.com/?a=b")
        self.assertEqual(out.count("?"), 1)


if __name__ == "__main__":
    unittest.main()
