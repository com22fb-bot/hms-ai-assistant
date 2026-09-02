import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault(
    "OAUTH_ENCRYPTION_KEY",
    "test-oauth-encryption-key-32chars!!",
)

from fastapi import HTTPException

from app.api.login_resolve import (
    LoginResolveRequest,
    WaitlistRequest,
    join_waitlist,
    resolve_login,
    resolve_mailbox_provider,
)
from app.middleware.authentication_context import AuthenticationContextMiddleware
from app.services.mail_domain import (
    classify_mail_domain,
    suggest_known_domain,
)


class _FakeRequest:
    def __init__(self, path: str) -> None:
        self.method = "POST"
        self.url = type("U", (), {"path": path})()
        self.client = type("C", (), {"host": "127.0.0.1"})()
        self.headers = {}


class LoginResolveTests(unittest.TestCase):
    def setUp(self) -> None:
        mx_patch = patch(
            "app.services.mail_domain.lookup_mx_hosts",
            return_value=[],
        )
        self.addCleanup(mx_patch.stop)
        mx_patch.start()
    def test_resolve_is_public(self) -> None:
        request = _FakeRequest("/auth/login/resolve")
        self.assertFalse(
            AuthenticationContextMiddleware._requires_identity(request)
        )

    def test_provider_from_domain(self) -> None:
        self.assertEqual(resolve_mailbox_provider("a@gmail.com"), "gmail")
        self.assertEqual(
            resolve_mailbox_provider("hsalcidor@yahoo.com"), "yahoo"
        )
        self.assertEqual(
            resolve_mailbox_provider("creechihuahua@yahoo.com.mx"), "yahoo"
        )
        self.assertEqual(
            resolve_mailbox_provider("Alguien@Yahoo.Com.Mx"), "yahoo"
        )
        self.assertEqual(resolve_mailbox_provider("x@outlook.com"), "hotmail")
        self.assertEqual(
            resolve_mailbox_provider("x@outlook.com.mx"), "hotmail"
        )
        self.assertEqual(
            resolve_mailbox_provider("x@hotmail.com.mx"), "hotmail"
        )
        self.assertEqual(resolve_mailbox_provider("x@empresa.mx"), "other")

    def test_hotmil_is_typo_for_hotmail(self) -> None:
        self.assertEqual(suggest_known_domain("hotmil.com"), "hotmail.com")
        verdict = classify_mail_domain("donexto@hotmil.com")
        self.assertEqual(verdict.status, "typo")
        self.assertEqual(verdict.suggested_email, "donexto@hotmail.com")
        self.assertIn("hotmail.com", verdict.message)
        self.assertIn("Hotmail", verdict.message)

    def test_hotmail_cox_is_typo_not_a_mailbox(self) -> None:
        self.assertEqual(suggest_known_domain("hotmail.cox"), "hotmail.com")
        verdict = classify_mail_domain("donexto@hotmail.cox")
        self.assertEqual(verdict.status, "typo")
        self.assertEqual(verdict.suggested_email, "donexto@hotmail.com")

    def test_hotmailer_cox_is_typo_not_subscribe(self) -> None:
        self.assertEqual(suggest_known_domain("hotmailer.cox"), "hotmail.com")
        with patch(
            "app.api.login_resolve.auth_user_exists", return_value=False
        ):
            result = resolve_login(
                LoginResolveRequest(email="donexto@hotmailer.cox")
            )
        self.assertEqual(result["next"], "fix_domain")
        self.assertEqual(result["suggested_email"], "donexto@hotmail.com")
        self.assertNotEqual(result["next"], "signup")

    def test_yahoo_com_mx_existing_goes_to_oauth(self) -> None:
        with patch(
            "app.api.login_resolve.auth_user_exists", return_value=True
        ):
            result = resolve_login(
                LoginResolveRequest(email="persona@yahoo.com.mx")
            )
        self.assertTrue(result["exists"])
        self.assertEqual(result["provider"], "yahoo")
        self.assertEqual(result["next"], "yahoo_oauth")

    def test_yahoo_com_mx_unknown_is_coming_soon(self) -> None:
        with patch(
            "app.api.login_resolve.auth_user_exists", return_value=False
        ):
            result = resolve_login(
                LoginResolveRequest(email="nuevo@yahoo.com.mx")
            )
        self.assertFalse(result["exists"])
        self.assertEqual(result["provider"], "yahoo")
        self.assertEqual(result["next"], "coming_soon_yahoo")
        self.assertIn("yahoo", result["pending_options"])
        self.assertEqual(result["active_options"], ["hotmail"])

    def test_existing_yahoo_goes_to_oauth(self) -> None:
        with patch(
            "app.api.login_resolve.auth_user_exists", return_value=True
        ):
            result = resolve_login(
                LoginResolveRequest(email="hsalcidor@yahoo.com")
            )
        self.assertTrue(result["exists"])
        self.assertEqual(result["next"], "yahoo_oauth")

    def test_unknown_yahoo_is_coming_soon_not_oauth(self) -> None:
        with patch(
            "app.api.login_resolve.auth_user_exists", return_value=False
        ):
            result = resolve_login(
                LoginResolveRequest(email="melgibson@yahoo.com")
            )
        self.assertFalse(result["exists"])
        self.assertEqual(result["next"], "coming_soon_yahoo")
        self.assertEqual(result["provider"], "yahoo")
        self.assertFalse(result["read_available"])

    def test_unknown_gmail_is_coming_soon(self) -> None:
        with patch(
            "app.api.login_resolve.auth_user_exists", return_value=False
        ):
            result = resolve_login(
                LoginResolveRequest(email="nuevo@gmail.com")
            )
        self.assertFalse(result["exists"])
        self.assertEqual(result["next"], "coming_soon_gmail")
        self.assertEqual(result["domain_status"], "pending_review")
        self.assertIn("Próximamente", result["message"])

    def test_unknown_icloud_is_pending_review(self) -> None:
        with patch(
            "app.api.login_resolve.auth_user_exists", return_value=False
        ):
            result = resolve_login(
                LoginResolveRequest(email="nuevo@icloud.com")
            )
        self.assertEqual(result["next"], "coming_soon_icloud")
        self.assertEqual(result["provider"], "apple")

    def test_existing_gmail_still_goes_to_google(self) -> None:
        with patch(
            "app.api.login_resolve.auth_user_exists", return_value=True
        ):
            result = resolve_login(
                LoginResolveRequest(email="ya@gmail.com")
            )
        self.assertEqual(result["next"], "google_oauth")

    def test_typo_hotmail_cox_asks_to_fix_domain(self) -> None:
        with patch(
            "app.api.login_resolve.auth_user_exists", return_value=False
        ):
            result = resolve_login(
                LoginResolveRequest(email="donexto@hotmail.cox")
            )
        self.assertEqual(result["next"], "fix_domain")
        self.assertEqual(result["suggested_email"], "donexto@hotmail.com")
        self.assertFalse(result["notified_support"])

    def test_typo_hotmil_asks_to_fix_domain(self) -> None:
        with patch(
            "app.api.login_resolve.auth_user_exists", return_value=False
        ):
            result = resolve_login(
                LoginResolveRequest(email="donexto@hotmil.com")
            )
        self.assertEqual(result["next"], "fix_domain")
        self.assertEqual(result["suggested_email"], "donexto@hotmail.com")
        self.assertFalse(result["notified_support"])
        self.assertIn("no coincide", result["message"])

    def test_missing_domain_does_not_notify(self) -> None:
        with (
            patch(
                "app.api.login_resolve.auth_user_exists", return_value=False
            ),
            patch(
                "app.services.mail_domain.domain_has_mail_records",
                return_value=False,
            ),
        ):
            result = resolve_login(
                LoginResolveRequest(email="alguien@sinservidor.test")
            )
        self.assertEqual(result["next"], "fix_domain")
        self.assertEqual(result["domain_status"], "missing")
        self.assertFalse(result["notified_support"])
        self.assertIn("no está activo", result["message"])

    def test_existing_unknown_domain_notifies_support(self) -> None:
        with (
            patch(
                "app.api.login_resolve.auth_user_exists", return_value=False
            ),
            patch(
                "app.services.mail_domain.domain_has_mail_records",
                return_value=True,
            ),
            patch(
                "app.api.login_resolve.notify_unsupported_domain_async",
                return_value=True,
            ) as notify,
        ):
            result = resolve_login(
                LoginResolveRequest(email="ana@empresa.mx")
            )
        self.assertEqual(result["next"], "unsupported_imap_domain")
        self.assertEqual(result["domain_status"], "unsupported")
        self.assertTrue(result["notified_support"])
        notify.assert_called_once()
        self.assertEqual(notify.call_args.args[1], "empresa.mx")
        self.assertIn("Microsoft 365", result["message"])

    def test_rejects_bad_email(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            resolve_login(LoginResolveRequest(email="not-an-email"))
        self.assertEqual(caught.exception.status_code, 400)

    def test_hotmail_named_is_live_azure(self) -> None:
        with patch(
            "app.api.login_resolve.auth_user_exists", return_value=False
        ):
            result = resolve_login(
                LoginResolveRequest(email="donexto@hotmail.com")
            )
        self.assertEqual(result["next"], "signup")
        self.assertEqual(result["provider"], "hotmail")
        self.assertTrue(result["read_available"])
        self.assertEqual(result["active_options"], ["hotmail"])

    def test_outlook_live_msn_are_live_microsoft(self) -> None:
        with patch(
            "app.api.login_resolve.auth_user_exists", return_value=False
        ):
            for address in (
                "ana@outlook.com",
                "ana@live.com",
                "ana@msn.com",
            ):
                result = resolve_login(LoginResolveRequest(email=address))
                self.assertEqual(result["next"], "signup", address)
                self.assertEqual(result["provider"], "hotmail", address)
                self.assertTrue(result["read_available"], address)

    def test_m365_onmicrosoft_is_available(self) -> None:
        with patch(
            "app.api.login_resolve.auth_user_exists", return_value=False
        ):
            result = resolve_login(
                LoginResolveRequest(email="ana@contoso.onmicrosoft.com")
            )
        self.assertEqual(result["provider"], "hotmail")
        self.assertEqual(result["next"], "signup")
        self.assertTrue(result["read_available"])

    def test_empresa_with_microsoft_mx_is_m365(self) -> None:
        with (
            patch(
                "app.api.login_resolve.auth_user_exists", return_value=False
            ),
            patch(
                "app.services.mail_domain.lookup_mx_hosts",
                return_value=["contoso.mail.protection.outlook.com"],
            ),
        ):
            result = resolve_login(
                LoginResolveRequest(email="ana@empresa.mx")
            )
        self.assertEqual(result["provider"], "hotmail")
        self.assertEqual(result["next"], "signup")
        self.assertTrue(result["read_available"])

    def test_random_empresa_is_unsupported_imap_not_pretend_read(self) -> None:
        with (
            patch(
                "app.api.login_resolve.auth_user_exists", return_value=False
            ),
            patch(
                "app.services.mail_domain.domain_has_mail_records",
                return_value=True,
            ),
        ):
            result = resolve_login(
                LoginResolveRequest(email="ana@empresa.mx")
            )
        self.assertEqual(result["next"], "unsupported_imap_domain")
        self.assertFalse(result["read_available"])
        self.assertIn("Microsoft 365", result["message"])

    def test_existing_gmail_tester_still_goes_to_google(self) -> None:
        with patch(
            "app.api.login_resolve.auth_user_exists", return_value=True
        ):
            result = resolve_login(
                LoginResolveRequest(email="hmcelinfo@gmail.com")
            )
        self.assertEqual(result["next"], "google_oauth")
        self.assertFalse(result["read_available"])

    def test_existing_yahoo_tester_still_goes_to_yahoo(self) -> None:
        with patch(
            "app.api.login_resolve.auth_user_exists", return_value=True
        ):
            result = resolve_login(
                LoginResolveRequest(email="hsalcidor@yahoo.com")
            )
        self.assertEqual(result["next"], "yahoo_oauth")
        self.assertFalse(result["read_available"])

    def test_waitlist_is_public(self) -> None:
        request = _FakeRequest("/auth/login/waitlist")
        self.assertFalse(
            AuthenticationContextMiddleware._requires_identity(request)
        )

    def test_waitlist_persists_email_and_provider(self) -> None:
        stored = {
            "status": "ok",
            "already": False,
            "email": "nuevo@gmail.com",
            "provider": "gmail",
            "created_at": "2026-09-02T00:00:00+00:00",
        }
        with patch(
            "app.api.login_resolve.persist_waitlist", return_value=stored
        ) as persist:
            result = join_waitlist(
                WaitlistRequest(email="nuevo@gmail.com", provider="gmail")
            )
        persist.assert_called_once_with("nuevo@gmail.com", "gmail")
        self.assertEqual(result["provider"], "gmail")
        self.assertIn("avisamos", result["message"])


if __name__ == "__main__":
    unittest.main()

