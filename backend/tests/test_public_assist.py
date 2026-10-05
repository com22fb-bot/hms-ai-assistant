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

    def test_tell_me_is_not_signup(self) -> None:
        # "cuenta" used to match inside "cuentame" and answer the signup pitch.
        for text in ("cuéntame", "cuentame", "Cuéntame más", "¿qué es Donexto?", "¿cómo funciona?", "tell me more"):
            self.assertEqual(assist.detect_intent(text), "what", text)
        self.assertEqual(assist.detect_intent("quiero crear una cuenta"), "start")
        self.assertEqual(assist.detect_intent("me di cuenta de algo"), "default")

    def test_mobile_questions(self) -> None:
        for text in (
            "que mal yo pensaba que eran una app para mi celular",
            "pensaba que eran app para celular",
            "¿Está en la Play Store?",
            "¿La puedo instalar en mi teléfono?",
            "is there a mobile app?",
        ):
            self.assertEqual(assist.detect_intent(text), "mobile", text)
        with patch.dict(os.environ, NO_AI):
            reply = assist.chat_reply(
                "m@example.com",
                [{"role": "user", "content": "pensaba que eran app para celular"}],
                "es",
            )["reply"]
        self.assertIn("app web", reply)
        self.assertIn("Play Store", reply)
        self.assertIn("aún no hay fecha", reply)

    def test_legal_questions_get_the_live_pages(self) -> None:
        for text in ("cuales son tus políticas?", "políticas", "tus terminos?", "¿Usan cookies?", "aviso de privacidad", "terms of service"):
            self.assertEqual(assist.detect_intent(text), "legal", text)
        with patch.dict(os.environ, NO_AI):
            reply = assist.chat_reply(
                "l@example.com", [{"role": "user", "content": "tus terminos?"}], "es"
            )["reply"]
        for url in (
            "https://www.donexto.com/privacidad.html",
            "https://www.donexto.com/terminos.html",
            "https://www.donexto.com/cookies.html",
        ):
            self.assertIn(url, reply)
        self.assertNotEqual(reply, assist.rule_reply("asdf", "es"))
        # Plain data-safety questions still get the privacy answer.
        self.assertEqual(assist.detect_intent("¿Es seguro? ¿leen mi contraseña?"), "privacy")

    def test_cancel_questions(self) -> None:
        for text in ("¿cómo me doy de baja?", "quiero borrar mi cuenta", "how do I cancel?"):
            self.assertEqual(assist.detect_intent(text), "cancel", text)
        self.assertIn("Eliminar cuenta", assist.rule_reply("¿cómo cancelo?", "es"))

    def test_facts_carry_the_product_manual(self) -> None:
        from app.services.contact_inbox import DONEXTO_REPLY_FACTS as facts

        for needle in (
            "privacidad.html", "terminos.html", "cookies.html", "support@donexto.com",
            "not yet a native app", "US$19.99", "banks, cards, Amazon", "read-only",
            "Outlook and Hotmail are live", "Delete account",
        ):
            self.assertIn(needle, facts)

    def test_banks_and_short_words_need_whole_tokens(self) -> None:
        self.assertEqual(assist.detect_intent("¿Se conecta a mi banco o a Amazon?"), "banks")
        self.assertEqual(assist.detect_intent("hi there"), "greeting")
        self.assertEqual(assist.detect_intent("this is nice"), "default")  # "hi" inside "this"

    def test_default_reply_differs_from_what(self) -> None:
        self.assertNotEqual(assist.rule_reply("asdf", "es"), assist.rule_reply("cuéntame", "es"))
        self.assertIn("Elige un tema (escribe el número o el nombre):", assist.rule_reply("asdf", "es"))

    def test_price_mentions_europe(self) -> None:
        reply = assist.rule_reply("precio", "es")
        self.assertIn("US$19.99", reply)
        self.assertIn("€19.99", reply)

    def test_ai_instructions_put_latest_question_first(self) -> None:
        captured: dict[str, str] = {}

        def fake(instructions: str, prompt: str, *, max_output_tokens: int) -> str:
            captured["instructions"], captured["prompt"] = instructions, prompt
            return "Hoy es una app web."

        with patch.object(assist, "ai_reply_configured", return_value=True), patch.object(
            assist, "_call_contact_ai", side_effect=fake
        ):
            assist.chat_reply("ai@example.com", [{"role": "user", "content": "¿hay app?"}], "es")
        self.assertIn("LATEST message first", captured["instructions"])
        self.assertIn("not yet a native app", captured["instructions"])
        self.assertIn("Visitor: ¿hay app?", captured["prompt"])

    def _dialog(self, assistant: str, user: str, lang: str = "es") -> dict:
        history = [
            {"role": "user", "content": "primera pregunta"},
            {"role": "assistant", "content": assistant},
            {"role": "user", "content": user},
        ]
        with patch.dict(os.environ, NO_AI):
            return assist.chat_reply("ctx@example.com", history, lang)

    def test_yes_follows_the_previous_offer(self) -> None:
        price = assist.rule_reply("precio", "es")
        self.assertIn("¿Quieres saber qué correos puedes conectar?", price)
        providers = assist.rule_reply("¿sirve con gmail?", "es")
        for answer in ("si", "Sí", "sí, por favor", "ok", "claro", "dale", "cuáles", "lo de los correos"):
            result = self._dialog(price, answer)
            self.assertEqual(result["intent"], "providers", answer)
            self.assertEqual(result["reply"], providers, answer)
        english = self._dialog(assist.rule_reply("price", "en"), "yes", "en")
        self.assertEqual(english["intent"], "providers")

    def test_no_closes_politely(self) -> None:
        price = assist.rule_reply("precio", "es")
        for answer in ("no", "No gracias", "nel", "ahorita no"):
            result = self._dialog(price, answer)
            self.assertEqual(result["intent"], "decline", answer)
            self.assertIn("sin problema", result["reply"])
            self.assertIn("\n1. Qué es Donexto", result["reply"])
            self.assertNotIn("No estoy seguro", result["reply"])

    def test_yes_to_a_multi_topic_offer_asks_which(self) -> None:
        result = self._dialog(assist.rule_reply("cuéntame", "es"), "si")
        self.assertEqual(result["intent"], "choose")
        self.assertIn("¿Por cuál empiezo:", result["reply"])
        self.assertIn("qué correos puedes conectar", result["reply"])
        self.assertNotIn("qué es Donexto", result["reply"])  # already explained

    def test_unclear_shows_numbered_menu(self) -> None:
        for lang, first, last in (("es", "1. Qué es Donexto", "8. Hablar con una persona"), ("en", "1. What Donexto is", "8. Talk to a person")):
            menu = assist.rule_reply("asdf qwerty", lang)
            lines = menu.split("\n")
            self.assertEqual(len(lines), 9)
            self.assertEqual(lines[1], first)
            self.assertEqual(lines[8], last)
            for index, line in enumerate(lines[1:], start=1):
                self.assertTrue(line.startswith(f"{index}. "), line)
        self.assertIn("2. Precio · Plan Normal (US$19.99 al mes)", assist.rule_reply("asdf", "es"))
        self.assertIn("6. Políticas, términos y cookies", assist.rule_reply("asdf", "es"))
        self.assertTrue(assist.rule_reply("hola", "es").startswith("¡Hola! Soy el asistente de Donexto. Elige un tema"))

    def test_menu_numbers_and_names_pick_the_topic(self) -> None:
        menu = assist.rule_reply("asdf", "es")
        expected = {
            "1": "what", "2": "price", "3": "providers", "4": "mobile", "5": "privacy",
            "6": "legal", "7": "start", "opción 3": "providers", "la 2": "price", "#6": "legal",
            "3.": "providers", "precio": "price", "correos": "providers", "web": "mobile",
            "privacidad": "privacy", "políticas": "legal", "empezar": "start",
        }
        with patch.object(assist, "notify_human_handoff", return_value=True):
            for answer, intent in expected.items():
                self.assertEqual(self._dialog(menu, answer)["intent"], intent, answer)
        self.assertEqual(self._dialog(menu, "9")["intent"], "default")
        self.assertIn("https://www.donexto.com/terminos.html", self._dialog(menu, "6")["reply"])

    def test_human_handoff_mails_support_once(self) -> None:
        menu = assist.rule_reply("asdf", "es")
        with patch.dict(os.environ, {**NO_AI, "RESEND_API_KEY": "re_test"}), patch(
            "app.services.support_notify.httpx.post"
        ) as post:
            post.return_value = SimpleNamespace(status_code=200)
            first = self._dialog(menu, "8")
            second = self._dialog(menu, "quiero hablar con una persona")
        self.assertEqual(first["intent"], "human")
        self.assertTrue(first["handoff"])
        self.assertIn("ya avisé al equipo", first["reply"])
        self.assertTrue(second["handoff"])
        self.assertEqual(post.call_count, 1)
        sent = post.call_args.kwargs["json"]
        self.assertEqual(sent["to"], ["support@donexto.com"])
        self.assertEqual(sent["reply_to"], "ctx@example.com")
        self.assertIn("Visitante: 8", sent["text"])

    def test_human_handoff_failure_points_to_support(self) -> None:
        with patch.object(assist, "_send_via_resend", side_effect=RuntimeError("down")):
            result = self._dialog("x", "quiero hablar con una persona")
        self.assertFalse(result["handoff"])
        self.assertIn("No pude avisar al equipo", result["reply"])

    def test_yes_without_context_stays_default(self) -> None:
        with patch.dict(os.environ, NO_AI):
            result = assist.chat_reply("solo@example.com", [{"role": "user", "content": "si"}], "es")
        self.assertEqual(result["intent"], "default")

    def test_real_questions_still_win_over_context(self) -> None:
        result = self._dialog(assist.rule_reply("precio", "es"), "si, ¿y es seguro?")
        self.assertEqual(result["intent"], "privacy")

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
            result = assist.chat_reply(
                "b@example.com", [{"role": "user", "content": "¿Cuánto cuesta el plan?"}], "es"
            )
        self.assertEqual(result["source"], "ai")
        self.assertIn("https://app.donexto.com/", result["reply"])
        self.assertNotIn("phish.example", result["reply"])

    def test_menu_picks_and_no_stay_on_rules_even_with_ai(self) -> None:
        with patch.object(assist, "ai_reply_configured", return_value=True), patch.object(
            assist, "_call_contact_ai", return_value="párrafo vago"
        ) as ai:
            picked = assist.chat_reply("m@example.com", [{"role": "user", "content": "3"}], "es")
            declined = assist.chat_reply(
                "m@example.com",
                [
                    {"role": "user", "content": "precio"},
                    {"role": "assistant", "content": "¿Quieres saber qué correos puedes conectar?"},
                    {"role": "user", "content": "no"},
                ],
                "es",
            )
            greeted = assist.chat_reply("m@example.com", [{"role": "user", "content": "hola"}], "es")
        ai.assert_not_called()
        self.assertEqual(picked["intent"], "providers")
        self.assertEqual(declined["intent"], "decline")
        self.assertIn("8. Hablar con una persona", declined["reply"])
        self.assertIn("1. Qué es Donexto", greeted["reply"])

    def test_ai_unsure_token_becomes_menu(self) -> None:
        with patch.object(assist, "ai_reply_configured", return_value=True), patch.object(
            assist, "_call_contact_ai", return_value="[[MENU]]"
        ):
            result = assist.chat_reply(
                "u@example.com",
                [{"role": "user", "content": "¿puedo usarlo para mi tienda de bicicletas?"}],
                "es",
            )
        self.assertEqual(result["source"], "rules")
        self.assertEqual(result["intent"], "default")
        self.assertIn("Elige un tema", result["reply"])
        self.assertIn("6. Políticas", result["reply"])

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
