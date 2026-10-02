"""Texto plano a partir de correos HTML (sin CSS en títulos/resúmenes)."""

import os
import unittest

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault("OAUTH_ENCRYPTION_KEY", "test-oauth-encryption-key-32chars!!")

from app.utils.html_text import html_to_text, strip_css_noise

AZURE_PREVIEW = (
    "table {width:640px} body[data-outlook-cycle] .container-wide .main-container > table "
    "{width:888px} } @media only screen and (max-width: 640px) { .outer-wrapper {width:100% "
    "!important} .inner {padding:0} } Tu factura de Azure está lista. Revisa el cobro de $12.40."
)


class StripCssNoiseTest(unittest.TestCase):
    def test_azure_preview_keeps_only_the_sentence(self) -> None:
        self.assertEqual(
            strip_css_noise(AZURE_PREVIEW),
            "Tu factura de Azure está lista. Revisa el cobro de $12.40.",
        )

    def test_truncated_css_becomes_empty(self) -> None:
        cut = AZURE_PREVIEW[:150]
        self.assertEqual(strip_css_noise(cut), "")

    def test_selector_leftovers_are_dropped(self) -> None:
        self.assertEqual(strip_css_noise("table {width:640px} body[data-outlook-cycle] .container-wide"), "")

    def test_plain_text_is_untouched(self) -> None:
        for text in (
            "Reunión a las 10:30 a.m. con el cliente.",
            "Tu pedido llega el jueves: $58.47.",
            "Hola Maya. Tu código es 123456.",
        ):
            self.assertEqual(strip_css_noise(text), text)

    def test_non_css_braces_keep_their_content(self) -> None:
        self.assertEqual(strip_css_noise("Pedido {123} listo"), "Pedido 123 listo")

    def test_outlook_classes(self) -> None:
        self.assertEqual(
            strip_css_noise(".ExternalClass {width:100%} .ExternalClass p, .ExternalClass span {line-height:100%} Your Microsoft Azure invoice"),
            "Your Microsoft Azure invoice",
        )


class HtmlToTextTest(unittest.TestCase):
    def test_style_and_head_are_dropped(self) -> None:
        body = (
            "<html><head><title>Azure</title><style>table {width:640px} @media only screen "
            "and (max-width: 640px) { .outer {width:100%} }</style></head>"
            "<body><!--[if mso]><table><tr><td><![endif]--><p>Hola&nbsp;Maya,</p>"
            "<p>Tu factura de <b>Azure</b> está lista.</p><script>alert(1)</script></body></html>"
        )
        self.assertEqual(html_to_text(body), "Hola Maya, Tu factura de Azure está lista.")

    def test_inline_css_text_in_body_is_cleaned(self) -> None:
        body = "<div>table {width:640px} .x {color:red}</div><div>Pago recibido</div>"
        self.assertEqual(html_to_text(body), "Pago recibido")

    def test_hostile_markup_stays_fast(self) -> None:
        import time

        for chunk in ("<script>xxxx", "<!--xx", "<style a", "<" * 4, "a:a a:a {b:c d:e f} ", "@media x "):
            body = chunk * (200_000 // len(chunk))
            started = time.perf_counter()
            html_to_text(body)
            self.assertLess(time.perf_counter() - started, 1.0, chunk)

    def test_unclosed_style_drops_the_rest(self) -> None:
        self.assertEqual(html_to_text("<p>Hola</p><style>table {width:640px}"), "Hola")

    def test_empty(self) -> None:
        self.assertEqual(html_to_text(None), "")
        self.assertEqual(html_to_text(""), "")


class MicrosoftBodyPartsTest(unittest.TestCase):
    def test_graph_html_body_has_no_css_text(self) -> None:
        from app.services.microsoft_import import _body_parts

        text, html_body = _body_parts(
            {
                "body": {
                    "contentType": "html",
                    "content": "<html><head><style>table {width:640px}</style></head>"
                    "<body><p>Your Azure invoice is ready</p></body></html>",
                },
                "bodyPreview": "table {width:640px} Your Azure invoice is ready",
            }
        )
        self.assertEqual(text, "Your Azure invoice is ready")
        self.assertIn("<style>", html_body)


if __name__ == "__main__":
    unittest.main()
