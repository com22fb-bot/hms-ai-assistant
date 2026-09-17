import unittest

from app.services.donexto_verification_email import build_verification_email


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


if __name__ == "__main__":
    unittest.main()