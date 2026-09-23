import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault(
    "OAUTH_ENCRYPTION_KEY",
    "test-oauth-encryption-key-32chars!!",
)

from app.security.origins import expand_frontend_origins
from app.security.redirect import sanitize_return_to


class SanitizeReturnToTests(unittest.TestCase):
    def test_rejects_suffix_attack_hosts(self) -> None:
        with patch("app.security.redirect.settings") as settings:
            settings.frontend_origins = [
                "https://app.donexto.com",
                "http://localhost:3000",
            ]
            self.assertEqual(
                sanitize_return_to("https://falsodonexto.com/phish"),
                "https://app.donexto.com/",
            )
            self.assertEqual(
                sanitize_return_to("https://evil.donexto.com.attacker.test/"),
                "https://app.donexto.com/",
            )

    def test_accepts_exact_allowlist_origins(self) -> None:
        with patch("app.security.redirect.settings") as settings:
            settings.frontend_origins = [
                "https://app.donexto.com",
                "http://localhost:3000",
            ]
            self.assertEqual(
                sanitize_return_to("https://app.donexto.com/admin"),
                "https://app.donexto.com/admin",
            )
            self.assertEqual(
                sanitize_return_to("https://app.donexto.com/admin/"),
                "https://app.donexto.com/admin",
            )
            self.assertEqual(
                sanitize_return_to("https://app.donexto.com/dashboard"),
                "https://app.donexto.com/",
            )
            self.assertEqual(
                sanitize_return_to("https://app.donexto.com/admin/extra"),
                "https://app.donexto.com/",
            )
            self.assertEqual(
                sanitize_return_to("http://localhost:3000/dashboard"),
                "http://localhost:3000/",
            )

    def test_rejects_unknown_host_even_with_donexto_substring(self) -> None:
        with patch("app.security.redirect.settings") as settings:
            settings.frontend_origins = ["http://127.0.0.1:3000"]
            self.assertEqual(
                sanitize_return_to("https://app.donexto.com"),
                "http://127.0.0.1:3000/",
            )

    def test_marketing_admin_origins_when_app_is_allowed(self) -> None:
        expanded = expand_frontend_origins(
            ["https://app.donexto.com/", "http://localhost:3000"]
        )
        self.assertEqual(
            expanded,
            [
                "https://app.donexto.com",
                "http://localhost:3000",
                "https://www.donexto.com",
                "https://donexto.com",
            ],
        )
        self.assertEqual(
            expand_frontend_origins(["http://localhost:3000"]),
            ["http://localhost:3000"],
        )
        with patch("app.security.redirect.settings") as settings:
            settings.frontend_origins = expanded
            self.assertEqual(
                sanitize_return_to("https://www.donexto.com/admin"),
                "https://www.donexto.com/admin",
            )
            self.assertEqual(
                sanitize_return_to("https://donexto.com/admin?x=1"),
                "https://donexto.com/admin",
            )
            self.assertEqual(
                sanitize_return_to("https://www.donexto.com/other"),
                "https://www.donexto.com/",
            )
            self.assertEqual(
                sanitize_return_to("https://not-donexto.example/admin"),
                "https://app.donexto.com/",
            )


if __name__ == "__main__":
    unittest.main()
