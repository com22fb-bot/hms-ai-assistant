"""Public landing contact: Resend HTTP only, no auth, no SMTP."""

from __future__ import annotations

import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault(
    "OAUTH_ENCRYPTION_KEY",
    "test-oauth-encryption-key-32chars!!",
)

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.public_contact import CONTACT_MAX_REQUESTS, router as public_contact_router
from app.middleware.authentication_context import AuthenticationContextMiddleware
from app.security.rate_limit import _hits
from app.services.support_notify import (
    DEFAULT_SUPPORT_EMAIL,
    PUBLIC_CONTACT_INBOX,
    send_public_contact_message,
    send_transactional_email,
    send_unsupported_domain_notice,
    support_notify_email,
)


def _app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(AuthenticationContextMiddleware)
    app.include_router(public_contact_router)
    return app


def _payload(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "name": "Alex",
        "email": "alex@example.com",
        "country": "MX",
        "message": "Quiero saber si Yahoo ya se lee.",
        "lang": "es",
        "website": "",
    }
    body.update(overrides)
    return body


class PublicContactTests(unittest.TestCase):
    def setUp(self) -> None:
        for key in list(_hits):
            if str(key).startswith("public-contact:"):
                del _hits[key]
        self._persist = patch(
            "app.api.public_contact.persist_public_contact",
            return_value="11111111-1111-1111-1111-111111111111",
        ).start()
        self.addCleanup(patch.stopall)

    def _client(self) -> TestClient:
        return TestClient(_app())

    def test_route_does_not_require_a_session(self) -> None:
        request = SimpleNamespace(method="POST", url=SimpleNamespace(path="/public/contact"))
        self.assertFalse(AuthenticationContextMiddleware._requires_identity(request))

    def test_success_uses_resend_http_even_when_smtp_host_is_set(self) -> None:
        with patch.dict(
            os.environ,
            {
                "RESEND_API_KEY": "re_test",
                "SUPPORT_SMTP_HOST": "smtp.resend.com",
                "SUPPORT_SMTP_FROM": "support@donexto.com",
            },
        ), patch("app.services.support_notify.httpx.post") as post, patch(
            "app.services.support_notify.smtplib.SMTP"
        ) as smtp, patch(
            "app.services.support_notify.smtplib.SMTP_SSL"
        ) as smtp_ssl:
            post.return_value = SimpleNamespace(status_code=200)
            response = self._client().post(
                "/public/contact",
                json=_payload(),
                headers={"X-Forwarded-For": "203.0.113.10"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        smtp.assert_not_called()
        smtp_ssl.assert_not_called()
        self.assertEqual(post.call_args.args[0], "https://api.resend.com/emails")
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["to"], [PUBLIC_CONTACT_INBOX])
        self.assertEqual(payload["reply_to"], "alex@example.com")
        self.assertEqual(payload["from"], "Donexto <support@donexto.com>")
        self.assertIn("Quiero saber si Yahoo ya se lee.", payload["text"])
        self.assertIn("alex@example.com", payload["text"])
        self.assertIn("https://www.donexto.com/admin?tab=mensajes", payload["text"])
        self.assertNotIn("html", payload)
        self._persist.assert_called_once()
        self.assertEqual(
            self._persist.call_args.kwargs["email"],
            "alex@example.com",
        )
        self.assertEqual(
            post.call_args.kwargs["headers"]["Authorization"],
            "Bearer re_test",
        )

    def test_honeypot_accepts_without_sending(self) -> None:
        with patch("app.services.support_notify.httpx.post") as post, patch(
            "app.services.support_notify.smtplib.SMTP"
        ) as smtp:
            response = self._client().post(
                "/public/contact",
                json=_payload(website="https://spam.example"),
                headers={"X-Forwarded-For": "203.0.113.11"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        post.assert_not_called()
        smtp.assert_not_called()
        self._persist.assert_not_called()

    def test_missing_message_is_rejected(self) -> None:
        response = self._client().post(
            "/public/contact",
            json=_payload(message="   "),
            headers={"X-Forwarded-For": "203.0.113.12"},
        )
        self.assertEqual(response.status_code, 422)

    def test_message_over_2000_chars_is_rejected(self) -> None:
        response = self._client().post(
            "/public/contact",
            json=_payload(message="a" * 2001),
            headers={"X-Forwarded-For": "203.0.113.13"},
        )
        self.assertEqual(response.status_code, 422)

    def test_invalid_email_is_rejected(self) -> None:
        response = self._client().post(
            "/public/contact",
            json=_payload(email="no-es-correo"),
            headers={"X-Forwarded-For": "203.0.113.14"},
        )
        self.assertEqual(response.status_code, 422)

    def test_resend_http_error_is_not_2xx(self) -> None:
        with patch.dict(os.environ, {"RESEND_API_KEY": "re_test"}), patch(
            "app.services.support_notify.httpx.post"
        ) as post:
            post.return_value = SimpleNamespace(status_code=422)
            response = self._client().post(
                "/public/contact",
                json=_payload(),
                headers={"X-Forwarded-For": "203.0.113.15"},
            )
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["detail"]["status"], "delivery_failed")
        self._persist.assert_not_called()

    def test_missing_resend_key_is_not_2xx_and_does_not_try_smtp(self) -> None:
        with patch.dict(
            os.environ,
            {"RESEND_API_KEY": "", "SUPPORT_SMTP_HOST": "smtp.resend.com"},
        ), patch("app.services.support_notify.smtplib.SMTP") as smtp, patch(
            "app.services.support_notify.httpx.post"
        ) as post:
            response = self._client().post(
                "/public/contact",
                json=_payload(),
                headers={"X-Forwarded-For": "203.0.113.16"},
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"]["status"], "delivery_unconfigured")
        smtp.assert_not_called()
        post.assert_not_called()
        self._persist.assert_not_called()

    def test_rate_limit_is_per_ip(self) -> None:
        with patch.dict(os.environ, {"RESEND_API_KEY": "re_test"}), patch(
            "app.services.support_notify.httpx.post"
        ) as post:
            post.return_value = SimpleNamespace(status_code=200)
            client = self._client()
            for _ in range(CONTACT_MAX_REQUESTS):
                ok = client.post(
                    "/public/contact",
                    json=_payload(),
                    headers={"X-Forwarded-For": "203.0.113.20"},
                )
                self.assertEqual(ok.status_code, 200)
            blocked = client.post(
                "/public/contact",
                json=_payload(),
                headers={"X-Forwarded-For": "203.0.113.20"},
            )
            other = client.post(
                "/public/contact",
                json=_payload(),
                headers={"X-Forwarded-For": "203.0.113.21"},
            )
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(other.status_code, 200)

    def test_unauthenticated_request_reaches_the_handler(self) -> None:
        with patch.dict(os.environ, {"RESEND_API_KEY": "re_test"}), patch(
            "app.services.support_notify.httpx.post"
        ) as post, patch(
            "app.middleware.authentication_context.authenticate_request"
        ) as authenticate:
            post.return_value = SimpleNamespace(status_code=200)
            response = self._client().post(
                "/public/contact",
                json=_payload(),
                headers={"X-Forwarded-For": "203.0.113.30"},
            )
        self.assertEqual(response.status_code, 200)
        authenticate.assert_not_called()


class SupportNotifyTransportTests(unittest.TestCase):
    def test_default_inbox_is_donexto(self) -> None:
        self.assertEqual(DEFAULT_SUPPORT_EMAIL, "support@donexto.com")
        self.assertEqual(PUBLIC_CONTACT_INBOX, "support@donexto.com")
        with patch.dict(os.environ, {"SUPPORT_NOTIFY_EMAIL": ""}):
            self.assertEqual(support_notify_email(), "support@donexto.com")

    def test_domain_alert_uses_resend_not_smtp(self) -> None:
        with patch.dict(
            os.environ,
            {
                "RESEND_API_KEY": "re_test",
                "SUPPORT_SMTP_HOST": "smtp.resend.com",
                "SUPPORT_NOTIFY_EMAIL": "",
                "SUPPORT_SMTP_FROM": "support@donexto.com",
            },
        ), patch(
            "app.services.support_notify.persist_domain_request"
        ) as persist, patch(
            "app.services.support_notify.httpx.post"
        ) as post, patch(
            "app.services.support_notify.smtplib.SMTP"
        ) as smtp, patch(
            "app.services.support_notify._send_via_formsubmit"
        ) as formsubmit:
            post.return_value = SimpleNamespace(status_code=200)
            delivered = send_unsupported_domain_notice(
                "person@example.com",
                "example.com",
            )
        self.assertTrue(delivered)
        smtp.assert_not_called()
        formsubmit.assert_not_called()
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["to"], ["support@donexto.com"])
        self.assertIn("person@example.com", payload["text"])
        persist.assert_called_once()

    def test_domain_alert_falls_back_to_formsubmit_without_smtp(self) -> None:
        with patch.dict(
            os.environ,
            {"RESEND_API_KEY": "", "SUPPORT_SMTP_HOST": "smtp.resend.com"},
        ), patch(
            "app.services.support_notify.persist_domain_request"
        ), patch(
            "app.services.support_notify.smtplib.SMTP"
        ) as smtp, patch(
            "app.services.support_notify._send_via_formsubmit",
            return_value=True,
        ) as formsubmit:
            delivered = send_unsupported_domain_notice(
                "person@example.com",
                "example.com",
            )
        self.assertTrue(delivered)
        smtp.assert_not_called()
        formsubmit.assert_called_once()

    def test_verification_mail_still_prefers_smtp_when_configured(self) -> None:
        smtp = MagicMock()
        with patch.dict(
            os.environ,
            {
                "SUPPORT_SMTP_HOST": "smtp.test",
                "SUPPORT_SMTP_PORT": "587",
                "SUPPORT_SMTP_FROM": "support@donexto.com",
                "RESEND_API_KEY": "re_test",
            },
        ), patch("app.services.support_notify.smtplib.SMTP") as smtp_cls, patch(
            "app.services.support_notify.httpx.post"
        ) as post:
            smtp_cls.return_value.__enter__.return_value = smtp
            delivered = send_transactional_email(
                "user@example.test",
                "Confirma tu correo",
                "cuerpo",
            )
        self.assertTrue(delivered)
        smtp.send_message.assert_called_once()
        post.assert_not_called()

    def test_public_contact_helper_sets_reply_to(self) -> None:
        with patch.dict(
            os.environ,
            {
                "RESEND_API_KEY": "re_test",
                "SUPPORT_SMTP_HOST": "smtp.resend.com",
                "SUPPORT_SMTP_FROM": "Donexto <support@donexto.com>",
            },
        ), patch("app.services.support_notify.httpx.post") as post, patch(
            "app.services.support_notify.smtplib.SMTP"
        ) as smtp:
            post.return_value = SimpleNamespace(status_code=200)
            delivered = send_public_contact_message(
                name="Ana\nGarcía",
                email="ana@example.com",
                country="US",
                message="Hola\ndesde la landing",
                lang="en",
            )
        self.assertTrue(delivered)
        smtp.assert_not_called()
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["reply_to"], "ana@example.com")
        self.assertEqual(payload["from"], "Donexto <support@donexto.com>")
        self.assertNotIn("\n", payload["subject"])
        self.assertIn("Ana García", payload["subject"])
        self.assertIn("Hola\ndesde la landing", payload["text"])


if __name__ == "__main__":
    unittest.main()
