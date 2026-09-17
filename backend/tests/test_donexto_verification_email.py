import os
import smtplib
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.donexto_verification_email import (
    action_link_from_generate_response,
    build_verification_email,
    send_verification_email,
)
from app.services.support_notify import SMTPDeliveryError


class DonextoVerificationEmailTests(unittest.TestCase):
    def test_spanish_email(self) -> None:
        message = build_verification_email("es", "https://example.test/link")
        self.assertEqual(message.subject, "Confirma tu correo de Donexto")
        self.assertIn("Confirma tu correo", message.body)

    def test_english_email(self) -> None:
        message = build_verification_email("en", "https://example.test/link")
        self.assertEqual(message.subject, "Confirm your Donexto email")
        self.assertIn("Confirm your Donexto email", message.body)

    def test_unknown_language_falls_back_to_spanish(self) -> None:
        message = build_verification_email("fr", "https://example.test/link")
        self.assertEqual(message.subject, "Confirma tu correo de Donexto")
        self.assertIn("Confirma tu correo", message.body)

    def test_extracts_action_link_from_supabase_response(self) -> None:
        response = SimpleNamespace(
            properties={"action_link": " https://example.test/action "}
        )
        self.assertEqual(
            action_link_from_generate_response(response),
            "https://example.test/action",
        )

    def test_sends_localized_email_with_supabase_action_link(self) -> None:
        client = MagicMock()
        smtp_password = "p" * 16
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
        smtp.login.assert_called_once_with(
            "sender@example.test", smtp_password
        )
        smtp.send_message.assert_called_once()
        sent_message = smtp.send_message.call_args.args[0]
        self.assertEqual(message.subject, "Confirm your Donexto email")
        self.assertIn("https://example.test/action", sent_message.get_content())
        client.auth.admin.generate_link.assert_called_once_with(
            {
                "type": "magiclink",
                "email": "recipient@example.test",
                "options": {
                    "redirect_to": "https://app.example.test/?donexto_verify=1"
                },
            }
        )

    def test_smtp_authentication_error_is_safe(self) -> None:
        client = MagicMock()
        smtp_password = "p" * 16
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
        smtp_password = "q" * 16
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
            smtp_class.side_effect = OSError("connection refused")
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


if __name__ == "__main__":
    unittest.main()