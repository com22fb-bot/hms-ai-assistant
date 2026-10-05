"""Asistencia: acuse automático, verificación de correo y chat. Sin base de datos."""

from __future__ import annotations

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault("OAUTH_ENCRYPTION_KEY", "test-oauth-encryption-key-32chars!!")

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.public_assist import router as assist_router
from app.api.public_contact import router as contact_router
from app.middleware.authentication_context import AuthenticationContextMiddleware
from app.security.rate_limit import _hits
from app.services import assist


def _app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(AuthenticationContextMiddleware)
    app.include_router(contact_router)
    app.include_router(assist_router)
    return app


def _clear_hits() -> None:
    for key in list(_hits):
        if str(key).startswith(("assist-", "public-contact:")):
            del _hits[key]


NO_AI = {"CONTACT_AI_PROVIDER": "off"}


class TokenTests(unittest.TestCase):
    def setUp(self) -> None:
        _clear_hits()

    def test_link_round_trip_gives_session(self) -> None:
        link = assist.assist_link("ana@example.com")
        self.assertTrue(link.startswith("https://app.donexto.com/asistencia?t="))
        token = link.split("?t=", 1)[1]
        result = assist.redeem_link(token)
        self.assertEqual(result["status"], "verified")
        self.assertEqual(assist.session_email(result["session"]), "ana@example.com")
        self.assertNotIn("ana@example.com", result["email"])

    def test_link_carries_language_for_non_spanish(self) -> None:
        self.assertNotIn("&lang=", assist.assist_link("a@example.com", "es-MX"))
        self.assertNotIn("&lang=", assist.assist_link("a@example.com"))
        self.assertTrue(assist.assist_link("a@example.com", "en").endswith("&lang=en"))
        self.assertTrue(assist.assist_link("a@example.com", "pt-BR").endswith("&lang=pt"))

    def test_forged_or_wrong_kind_tokens_fail(self) -> None:
        token = assist.sign_token("link", "ana@example.com", 60)
        body, sig = token.split(".")
        with self.assertRaises(assist.AssistTokenError):
            assist.read_token(f"{body}x.{sig}", "link")
        with self.assertRaises(assist.AssistTokenError):
            assist.read_token(token, "session")  # link is not a session

    def test_expired_token_fails(self) -> None:
        token = assist.sign_token("session", "ana@example.com", -5)
        with self.assertRaises(assist.AssistTokenError) as ctx:
            assist.read_token(token, "session")
        self.assertEqual(str(ctx.exception), "expired")

    def test_code_challenge_verifies_only_right_code(self) -> None:
        code, challenge = assist.new_code_challenge("leo@example.com")
        wrong = "000000" if code != "000000" else "111111"
        with self.assertRaises(assist.AssistTokenError):
            assist.verify_code(challenge, wrong)
        result = assist.verify_code(challenge, code)
        self.assertEqual(assist.session_email(result["session"]), "leo@example.com")

    def test_code_attempts_are_capped(self) -> None:
        code, challenge = assist.new_code_challenge("max@example.com")
        wrong = "000000" if code != "000000" else "111111"
        for _ in range(5):
            with self.assertRaises(assist.AssistTokenError):
                assist.verify_code(challenge, wrong)
        with self.assertRaises(assist.AssistTokenError) as ctx:
            assist.verify_code(challenge, code)
        self.assertEqual(str(ctx.exception), "too_many_attempts")

    def test_no_secret_means_unavailable(self) -> None:
        with patch.dict(os.environ, {"OAUTH_ENCRYPTION_KEY": "", "ASSIST_TOKEN_SECRET": ""}):
            self.assertFalse(assist.assist_available())
            with self.assertRaises(assist.AssistUnavailable):
                assist.sign_token("link", "a@b.co", 60)

    def test_signing_key_is_not_the_encryption_key(self) -> None:
        self.assertNotEqual(assist._signing_key(), os.environ["OAUTH_ENCRYPTION_KEY"].encode())


class AutoReplyTests(unittest.TestCase):
    def setUp(self) -> None:
        _clear_hits()
        assist._page_check.update(ok_until=0.0, down_until=0.0)
        self._live = patch.object(assist, "assist_page_live", return_value=True)
        self._live.start()
        self.addCleanup(self._live.stop)

    def test_without_live_page_the_reply_has_no_link(self) -> None:
        with patch.dict(os.environ, NO_AI):
            mail = assist.build_autoreply(
                name="Ana", email="ana@example.com", message="x", lang="es", include_link=False
            )
        self.assertNotIn("asistencia?t=", mail.body)
        self.assertNotIn("asistencia?t=", mail.html)
        self.assertIn("responde a este correo", mail.body)

    def test_page_check_caches_and_handles_errors(self) -> None:
        self._live.stop()
        try:
            with patch("httpx.get", return_value=SimpleNamespace(status_code=404)) as get:
                self.assertFalse(assist.assist_page_live())
                self.assertFalse(assist.assist_page_live())
            self.assertEqual(get.call_count, 1)
            assist._page_check.update(ok_until=0.0, down_until=0.0)
            with patch("httpx.get", return_value=SimpleNamespace(status_code=200)) as get:
                self.assertTrue(assist.assist_page_live())
                self.assertTrue(assist.assist_page_live())
            self.assertEqual(get.call_count, 1)
            assist._page_check.update(ok_until=0.0, down_until=0.0)
            with patch("httpx.get", return_value=SimpleNamespace(status_code=403)):
                self.assertTrue(assist.assist_page_live())
            assist._page_check.update(ok_until=0.0, down_until=0.0)
            with patch("httpx.get", return_value=SimpleNamespace(status_code=502)):
                self.assertFalse(assist.assist_page_live())
            assist._page_check.update(ok_until=0.0, down_until=0.0)
            with patch("httpx.get", side_effect=RuntimeError("dns")):
                self.assertFalse(assist.assist_page_live())
        finally:
            assist._page_check.update(ok_until=0.0, down_until=0.0)
            self._live.start()

    def test_send_skips_link_when_page_is_down(self) -> None:
        self._live.stop()
        try:
            with patch.object(assist, "assist_page_live", return_value=False), patch.dict(
                os.environ, {**NO_AI, "RESEND_API_KEY": "re_test"}
            ), patch("app.services.support_notify.httpx.post") as post:
                post.return_value = SimpleNamespace(status_code=200)
                self.assertTrue(
                    assist.send_contact_autoreply(name="A", email="down@example.com", message="m", lang="es")
                )
            self.assertNotIn("asistencia?t=", post.call_args.kwargs["json"]["text"])
        finally:
            self._live.start()

    def test_template_without_ai_has_link_and_service_info(self) -> None:
        with patch.dict(os.environ, NO_AI):
            mail = assist.build_autoreply(
                name="Ana López", email="ana@example.com", message="¿Cuánto cuesta?", lang="es"
            )
        self.assertIn("Hola Ana,", mail.body)
        self.assertIn("Contacta asistencia personalizada: https://app.donexto.com/asistencia?t=", mail.body)
        self.assertIn("Plan Normal", mail.body)
        self.assertIn("solo lectura", mail.body)
        self.assertIn("Contacta asistencia personalizada</a>", mail.html)
        self.assertEqual(mail.subject, "Recibimos tu mensaje · Donexto")

    def test_english_template(self) -> None:
        with patch.dict(os.environ, NO_AI):
            mail = assist.build_autoreply(name="", email="a@example.com", message="hi", lang="en")
        self.assertTrue(mail.body.startswith("Hi,"))
        self.assertIn("Contact personal assistance: https://app.donexto.com/asistencia?t=", mail.body)

    def test_ai_paragraph_is_included_without_links(self) -> None:
        with patch.object(assist, "ai_reply_configured", return_value=True), patch.object(
            assist,
            "_call_contact_ai",
            return_value="Sí, Outlook funciona hoy. Visita https://evil.example para más.",
        ):
            mail = assist.build_autoreply(name="Ana", email="ana@example.com", message="Outlook?", lang="es")
        self.assertIn("Sí, Outlook funciona hoy.", mail.body)
        self.assertNotIn("evil.example", mail.body)
        self.assertNotIn("evil.example", mail.html)

    def test_ai_failure_falls_back_to_template(self) -> None:
        with patch.object(assist, "ai_reply_configured", return_value=True), patch.object(
            assist, "_call_contact_ai", side_effect=RuntimeError("boom")
        ):
            mail = assist.build_autoreply(name="Ana", email="ana@example.com", message="x", lang="es")
        self.assertIn("asistencia?t=", mail.body)

    def test_send_once_per_inbox_and_from_support(self) -> None:
        with patch.dict(os.environ, {**NO_AI, "RESEND_API_KEY": "re_test"}), patch(
            "app.services.support_notify.httpx.post"
        ) as post:
            post.return_value = SimpleNamespace(status_code=200)
            first = assist.send_contact_autoreply(name="A", email="dup@example.com", message="m", lang="es")
            second = assist.send_contact_autoreply(name="A", email="dup@example.com", message="m", lang="es")
        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(post.call_count, 1)
        sent = post.call_args.kwargs["json"]
        self.assertEqual(sent["to"], ["dup@example.com"])
        self.assertEqual(sent["reply_to"], "support@donexto.com")
        self.assertIn("html", sent)

    def test_send_never_raises(self) -> None:
        with patch.object(assist, "build_autoreply", side_effect=RuntimeError("x")):
            self.assertFalse(
                assist.send_contact_autoreply(name="A", email="err@example.com", message="m", lang="es")
            )

    def test_contact_form_schedules_autoreply_after_support_mail(self) -> None:
        with patch.dict(os.environ, {"RESEND_API_KEY": "re_test"}), patch(
            "app.services.support_notify.httpx.post"
        ) as post, patch("app.api.public_contact.persist_public_contact"), patch(
            "app.api.public_contact.send_contact_autoreply"
        ) as autoreply:
            post.return_value = SimpleNamespace(status_code=200)
            response = TestClient(_app()).post(
                "/public/contact",
                json={"name": "Ana", "email": "Ana@Example.com", "message": "Hola", "lang": "es"},
                headers={"X-Forwarded-For": "198.51.100.40"},
            )
        self.assertEqual(response.status_code, 200)
        autoreply.assert_called_once_with(
            name="Ana", email="ana@example.com", message="Hola", lang="es"
        )

    def test_honeypot_does_not_autoreply(self) -> None:
        with patch("app.api.public_contact.send_contact_autoreply") as autoreply:
            response = TestClient(_app()).post(
                "/public/contact",
                json={"email": "bot@example.com", "message": "x", "website": "spam"},
                headers={"X-Forwarded-For": "198.51.100.41"},
            )
        self.assertEqual(response.status_code, 200)
        autoreply.assert_not_called()


class ChatTests(unittest.TestCase):
    def setUp(self) -> None:
        _clear_hits()

    def test_rule_intents(self) -> None:
        self.assertEqual(assist.detect_intent("¿Cuánto cuesta el plan?"), "price")
        self.assertEqual(assist.detect_intent("¿Sirve con Gmail?"), "providers")
        self.assertEqual(assist.detect_intent("¿Es seguro? ¿Leen mi contraseña?"), "privacy")
        self.assertEqual(assist.detect_intent("Quiero hablar con una persona"), "human")
        self.assertEqual(assist.detect_intent("Hola"), "greeting")
        self.assertEqual(assist.detect_intent("xyz"), "default")

    def test_rules_answer_when_ai_off(self) -> None:
        with patch.dict(os.environ, NO_AI):
            result = assist.chat_reply(
                "a@example.com", [{"role": "user", "content": "¿Cuánto cuesta?"}], "es"
            )
        self.assertEqual(result["source"], "rules")
        self.assertIn("$19.99", result["reply"])
        self.assertEqual(result["cta"]["url"], "https://app.donexto.com/")

    def test_ai_reply_strips_foreign_links_and_keeps_donexto(self) -> None:
        with patch.object(assist, "ai_reply_configured", return_value=True), patch.object(
            assist,
            "_call_contact_ai",
            return_value="Entra a https://app.donexto.com/ o a https://phish.example/x.",
        ):
            result = assist.chat_reply("b@example.com", [{"role": "user", "content": "Hola"}], "es")
        self.assertEqual(result["source"], "ai")
        self.assertIn("https://app.donexto.com/", result["reply"])
        self.assertNotIn("phish.example", result["reply"])

    def test_ai_failure_uses_rules(self) -> None:
        with patch.object(assist, "ai_reply_configured", return_value=True), patch.object(
            assist, "_call_contact_ai", side_effect=RuntimeError("down")
        ):
            result = assist.chat_reply("c@example.com", [{"role": "user", "content": "precio"}], "es")
        self.assertEqual(result["source"], "rules")

    def test_mailbox_ai_provider_is_never_read(self) -> None:
        with patch.dict(os.environ, {**NO_AI, "AI_PROVIDER": "openai"}):
            result = assist.chat_reply("d@example.com", [{"role": "user", "content": "hola"}], "es")
        self.assertEqual(result["source"], "rules")

    def test_history_must_end_with_visitor(self) -> None:
        with self.assertRaises(ValueError):
            assist.chat_reply("e@example.com", [{"role": "assistant", "content": "hola"}], "es")


class AssistApiTests(unittest.TestCase):
    def setUp(self) -> None:
        _clear_hits()
        self.client = TestClient(_app())

    def test_routes_are_public(self) -> None:
        for path in ("/public/assist/start", "/public/assist/verify", "/public/assist/redeem", "/public/assist/chat"):
            request = SimpleNamespace(method="POST", url=SimpleNamespace(path=path))
            self.assertFalse(AuthenticationContextMiddleware._requires_identity(request))

    def test_start_mails_code_then_verify_then_chat(self) -> None:
        captured: dict[str, str] = {}

        def fake_send(email: str, code: str, lang: str) -> bool:
            captured["email"], captured["code"] = email, code
            return True

        with patch("app.api.public_assist.send_code_email", side_effect=fake_send):
            started = self.client.post(
                "/public/assist/start",
                json={"email": " Leo@Example.com ", "lang": "es"},
                headers={"X-Forwarded-For": "198.51.100.1"},
            )
        self.assertEqual(started.status_code, 200)
        body = started.json()
        self.assertEqual(body["status"], "sent")
        self.assertNotIn(captured["code"], str(body))
        self.assertEqual(captured["email"], "leo@example.com")

        bad = self.client.post(
            "/public/assist/verify",
            json={"challenge": body["challenge"], "code": "12345x"},
        )
        self.assertEqual(bad.status_code, 400)

        ok = self.client.post(
            "/public/assist/verify",
            json={"challenge": body["challenge"], "code": captured["code"]},
        )
        self.assertEqual(ok.status_code, 200)
        session = ok.json()["session"]

        with patch.dict(os.environ, NO_AI):
            chat = self.client.post(
                "/public/assist/chat",
                json={"session": session, "messages": [{"role": "user", "content": "¿Es seguro?"}]},
            )
        self.assertEqual(chat.status_code, 200)
        self.assertIn("solo lectura", chat.json()["reply"])

    def test_start_rate_limited_per_email(self) -> None:
        with patch("app.api.public_assist.send_code_email", return_value=True):
            codes = [
                self.client.post(
                    "/public/assist/start",
                    json={"email": "rl@example.com"},
                    headers={"X-Forwarded-For": f"198.51.100.{i + 10}"},
                ).status_code
                for i in range(4)
            ]
        self.assertEqual(codes, [200, 200, 200, 429])

    def test_start_honeypot_sends_nothing(self) -> None:
        with patch("app.api.public_assist.send_code_email") as send:
            response = self.client.post(
                "/public/assist/start",
                json={"email": "bot@example.com", "website": "x"},
                headers={"X-Forwarded-For": "198.51.100.30"},
            )
        self.assertEqual(response.status_code, 200)
        send.assert_not_called()

    def test_start_invalid_email(self) -> None:
        response = self.client.post(
            "/public/assist/start",
            json={"email": "not-an-email"},
            headers={"X-Forwarded-For": "198.51.100.31"},
        )
        self.assertEqual(response.status_code, 422)

    def test_redeem_link_and_bad_link(self) -> None:
        token = assist.assist_link("ana@example.com").split("?t=", 1)[1]
        ok = self.client.post("/public/assist/redeem", json={"token": token})
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.json()["status"], "verified")
        bad = self.client.post("/public/assist/redeem", json={"token": token[:-3] + "abc"})
        self.assertEqual(bad.status_code, 400)

    def test_chat_requires_valid_session(self) -> None:
        link_token = assist.sign_token("link", "ana@example.com", 60)
        response = self.client.post(
            "/public/assist/chat",
            json={"session": link_token, "messages": [{"role": "user", "content": "hola"}]},
        )
        self.assertEqual(response.status_code, 401)

    def test_expired_session(self) -> None:
        session = assist.sign_token("session", "ana@example.com", -1)
        response = self.client.post(
            "/public/assist/chat",
            json={"session": session, "messages": [{"role": "user", "content": "hola"}]},
        )
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
