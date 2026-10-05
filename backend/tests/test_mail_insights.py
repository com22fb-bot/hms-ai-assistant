"""Rule-based mail cleaning + insights on anonymised real-pattern fixtures."""

from __future__ import annotations

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from mail_fixtures import FIXTURES  # noqa: E402

from app.services.mail_insights import (  # noqa: E402
    KIND_AREA,
    LANGS,
    build_insight,
    safe_insight,
    verified_excerpts,
)
from app.utils.mail_clean import (  # noqa: E402
    clean_email,
    clean_subject,
    import_body,
    is_stub_text,
    repair_mojibake,
)

INVISIBLE = ("\u034f", "\u200b", "\u200c", "\u00ad", "\u2007", "\ufeff")


class FixtureInsightTests(unittest.TestCase):
    def test_there_are_about_thirty_patterns(self) -> None:
        self.assertGreaterEqual(len(FIXTURES), 30)

    def test_kind_area_main_idea_quotes_and_facts(self) -> None:
        for fixture in FIXTURES:
            with self.subTest(fixture["name"]):
                insight = build_insight(fixture)
                self.assertEqual(insight["kind"], fixture["kind"])
                self.assertEqual(insight["area"], fixture["area"])
                for word in fixture["idea"]:
                    self.assertIn(word, insight["main_idea"]["es"])
                for quote in fixture["quotes"]:
                    self.assertTrue(
                        any(quote in excerpt for excerpt in insight["excerpts"]),
                        f"{quote!r} not in {insight['excerpts']!r}",
                    )
                for key, value in fixture["facts"].items():
                    self.assertEqual(insight["facts"].get(key), value, key)

    def test_quotes_are_exact_substrings_of_the_cleaned_text(self) -> None:
        for fixture in FIXTURES:
            with self.subTest(fixture["name"]):
                clean = clean_email(fixture["body_text"], fixture["body_html"], clean_subject(fixture["subject"]))
                insight = build_insight(fixture)
                self.assertLessEqual(len(insight["excerpts"]), 3)
                for quote in insight["excerpts"]:
                    self.assertIn(quote, clean.text)

    def test_facts_are_copied_from_the_email(self) -> None:
        for fixture in FIXTURES:
            with self.subTest(fixture["name"]):
                subject = clean_subject(fixture["subject"])
                clean = clean_email(fixture["body_text"], fixture["body_html"], subject)
                facts = build_insight(fixture)["facts"]
                for key in ("amount", "due_date", "date", "reference", "card_last4"):
                    if facts.get(key):
                        self.assertTrue(facts[key] in clean.text or facts[key] in subject, (key, facts[key]))
                if facts.get("merchant"):
                    self.assertTrue(facts["merchant"] in clean.text or facts["merchant"] in subject)

    def test_main_idea_in_five_languages_without_noise(self) -> None:
        for fixture in FIXTURES:
            with self.subTest(fixture["name"]):
                insight = build_insight(fixture)
                self.assertEqual(set(insight["main_idea"]), set(LANGS))
                for lang, sentence in insight["main_idea"].items():
                    self.assertTrue(10 <= len(sentence) <= 240, (lang, sentence))
                    self.assertNotIn("None", sentence)
                    self.assertNotIn("{", sentence)
                    self.assertNotIn("..", sentence)
                    self.assertFalse(any(ch in sentence for ch in INVISIBLE))

    def test_outputs_have_no_html_css_padding_or_tracking(self) -> None:
        for fixture in FIXTURES:
            with self.subTest(fixture["name"]):
                insight = build_insight(fixture)
                blob = " ".join([insight["preview"], *insight["excerpts"]])
                self.assertNotRegex(blob, r"<[a-zA-Z/][^>]*>")
                self.assertNotIn("&nbsp;", blob)
                self.assertNotIn("@media", blob)
                self.assertNotIn("open.gif", blob)
                self.assertFalse(any(ch in blob for ch in INVISIBLE), fixture["name"])
                for absent in fixture.get("absent", []):
                    self.assertNotIn(absent, blob)
                if fixture.get("no_digits_in_quotes"):
                    self.assertFalse(any(any(c.isdigit() for c in q) for q in insight["excerpts"]))

    def test_deterministic(self) -> None:
        for fixture in FIXTURES:
            first = json.dumps(build_insight(fixture), sort_keys=True, ensure_ascii=False)
            second = json.dumps(build_insight(dict(fixture)), sort_keys=True, ensure_ascii=False)
            self.assertEqual(first, second, fixture["name"])

    def test_area_is_never_health_for_loans_and_never_orders_for_cards(self) -> None:
        by_name = {fixture["name"]: build_insight(fixture) for fixture in FIXTURES}
        self.assertEqual(by_name["issste_fopi"]["area"], "bills")
        self.assertEqual(by_name["santander_card_not_delivered"]["area"], "money")
        self.assertTrue(set(KIND_AREA.values()) <= {
            "money", "orders", "subscriptions", "work", "home", "health", "bills", "travel",
            "security", "government", "insurance", "education", "social", "events", "promos", "other",
        })


class CleanerTests(unittest.TestCase):
    def test_mojibake_is_repaired_and_clean_text_is_untouched(self) -> None:
        self.assertEqual(repair_mojibake("AtenciÃ³n â€” Â¡Hola!"), "Atención — ¡Hola!")
        self.assertEqual(repair_mojibake("Atención — ¡Hola!"), "Atención — ¡Hola!")

    def test_rfc2047_subject(self) -> None:
        self.assertEqual(clean_subject("=?UTF-8?Q?Notificaci=C3=B3n?="), "Notificación")

    def test_html_only_mail_is_read_from_html(self) -> None:
        fixture = FIXTURES[0]
        self.assertTrue(is_stub_text(fixture["body_text"], fixture["subject"]))
        clean = clean_email(fixture["body_text"], fixture["body_html"], fixture["subject"])
        self.assertEqual(clean.source, "html")
        self.assertIn("Monto de rechazo: $159", clean.text)
        self.assertNotIn("Este correo se constituye", clean.text)
        self.assertNotIn("color:#333", clean.text)

    def test_quoted_history_signature_and_disclaimer_are_cut(self) -> None:
        text = (
            "Gracias, lo reviso hoy.\n\nEnviado desde mi iPhone\n\n"
            "On Thu, Oct 1, 2026 at 10:00 AM Persona <p@example.com> wrote:\n> texto anterior"
        )
        clean = clean_email(text, None, "Re: algo")
        self.assertEqual(clean.text, "Gracias, lo reviso hoy.")
        self.assertGreater(clean.removed.get("quoted", 0) + clean.removed.get("signature", 0), 0)

    def test_forwarded_content_is_kept(self) -> None:
        text = "---------- Forwarded message ---------\nDe: Banco <b@x.example>\nAsunto: Pago\n\nTu pago de $10.00 fue aplicado."
        clean = clean_email(text, None, "Fwd: Pago")
        self.assertIn("Tu pago de $10.00 fue aplicado.", clean.text)

    def test_hostile_input_is_bounded(self) -> None:
        clean = clean_email("x", "<style>" * 20000 + "<p>Hola mundo, esto es una prueba larga.</p>", "x")
        self.assertIsInstance(clean.text, str)

    def test_import_body_for_html_only_mail(self) -> None:
        fixture = FIXTURES[0]
        body, snippet = import_body(fixture["subject"], fixture["body_html"], fixture["subject"])
        self.assertIn("Monto de rechazo:", body)
        self.assertIn("$159", body)
        self.assertNotEqual(snippet, fixture["subject"])
        self.assertLessEqual(len(snippet), 280)
        self.assertFalse(any(ch in snippet for ch in INVISIBLE))

    def test_import_body_keeps_real_plain_text(self) -> None:
        text = "Hola, te confirmo la reunión del martes a las 10:00 en la oficina central. Saludos cordiales."
        body, snippet = import_body(text, "<p>otra cosa</p>", "Reunión")
        self.assertEqual(body, text)
        self.assertTrue(snippet.startswith("Hola, te confirmo"))

    def test_import_body_cleans_gmail_snippet_padding(self) -> None:
        body, snippet = import_body("", "", "Oferta", "Oferta\u034f\u200c\u00ad\u034f solo hoy")
        self.assertEqual(snippet, "Oferta solo hoy")
        self.assertEqual(body, "Oferta solo hoy")


class SafetyTests(unittest.TestCase):
    def test_verified_excerpts_drops_anything_not_in_text(self) -> None:
        clean = clean_email("Monto: $10.00\nGracias.", None, "x")
        self.assertEqual(verified_excerpts(["Monto: $10.00", "Monto: $99.00"], clean), ["Monto: $10.00"])

    def test_safe_insight_never_raises(self) -> None:
        self.assertIsNone(safe_insight(None))
        self.assertIsNotNone(safe_insight({"subject": None, "sender": None, "body_text": None}))


if __name__ == "__main__":
    unittest.main()


class LineJoinTests(unittest.TestCase):
    """Label/value tables and hard-wrapped text become whole, quotable lines."""

    def test_label_value_pairs_are_joined_with_one_space(self) -> None:
        from app.utils.mail_clean import clean_email

        html = "<table><tr><td>Monto de rechazo:<br>$751.28</td></tr><tr><td>Importe</td></tr><tr><td>$100</td></tr></table>"
        clean = clean_email("Rechazo", html, "Rechazo")
        self.assertIn("Monto de rechazo: $751.28", clean.lines)
        self.assertIn("Importe $100", clean.lines)

    def test_hard_wrapped_sentences_are_rejoined(self) -> None:
        from app.utils.mail_clean import clean_email

        text = (
            "Sentimos comunicarle que su pago no ha sido autorizado.\n\n"
            "Es posible que el número de tarjeta, la fecha de expiración o\n"
            "el código se haya introducido incorrectamente.\nAtentamente,\nEl equipo"
        )
        clean = clean_email(text, None, "Pago no autorizado")
        self.assertIn("Es posible que el número de tarjeta, la fecha de expiración o el código se haya introducido incorrectamente.", clean.lines)
        # Capitalised next lines are separate statements and stay separate.
        self.assertIn("El equipo", " ".join(clean.lines))
        self.assertNotIn("Atentamente, El equipo", clean.lines)

    def test_view_online_header_is_dropped(self) -> None:
        from app.utils.mail_clean import clean_email

        clean = clean_email("x", "<div>La solución para tu casa</div><p>ver online &gt;</p>", "Promo")
        self.assertEqual(clean.lines, ["La solución para tu casa"])

    def test_marketing_subdomains_count_as_promo_only_as_fallback(self) -> None:
        from app.services.mail_insights import build_insight

        promo = build_insight({"subject": "Nueva lavadora", "sender": "Marca <x@mx.email.marca.com>", "body_text": "", "body_html": "<p>La solución definitiva para tu ropa</p>"})
        self.assertEqual(promo["kind"], "promo")
        card = build_insight({
            "subject": "No fue posible entregar tu Tarjeta", "sender": "Banco <info@envio.banco.com.mx>", "body_text": "",
            "body_html": "<p>No fue posible entregar tu Tarjeta de Debito terminación 0000.</p>",
        })
        self.assertEqual(card["kind"], "card_status")
