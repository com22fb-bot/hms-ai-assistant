"""Plain-text extraction for HTML email bodies (stdlib only).

Naive tag stripping keeps the contents of ``<style>`` blocks, so newsletters
(e.g. Microsoft/Azure) ended up with previews such as
``table {width:640px} @media only screen and (max-width: 640px) { … }``.
``html_to_text`` drops head/style/script/comments before removing tags, and
``strip_css_noise`` cleans CSS that is already in a text (stored snippets,
Graph ``bodyPreview``). Mirrors frontend/lib/nucleo/cleanText.ts.
"""

from __future__ import annotations

import html
import re

_BLOCKS = re.compile(
    r"<(head|style|script|noscript|title|xml)\b[^>]*>.*?</\1\s*>",
    re.IGNORECASE | re.DOTALL,
)
_COMMENTS = re.compile(r"<!--.*?-->", re.DOTALL)
_CONDITIONAL = re.compile(r"<!\[if[^\]]*\]>.*?<!\[endif\]>", re.IGNORECASE | re.DOTALL)
_BREAKS = re.compile(r"<\s*(br|/p|/div|/tr|/li|/h[1-6])\b[^>]*>", re.IGNORECASE)
_TAGS = re.compile(r"<[^>]+>")
_CSS_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)

_TAG_NAMES = {
    "html", "body", "table", "tbody", "thead", "tfoot", "tr", "td", "th", "div", "span", "p",
    "a", "img", "ul", "ol", "li", "h1", "h2", "h3", "h4", "h5", "h6", "center", "font", "b",
    "i", "u", "strong", "em", "section", "header", "footer", "main", "article", "nav", "sup",
    "sub", "hr", "br", "blockquote", "pre", "code", "input", "button", "form", "label", "o",
    "v", "*",
}
_MEDIA_WORDS = {"only", "screen", "and", "not", "print", "all", "speech", "or", ">", "+", "~", ","}
_DECLARATIONS = re.compile(r"^(?:\s*[-\w]+\s*:\s*[^;{}]*;?)+\s*$")
_SELECTOR_CHARS = re.compile(r"[.#\[\]>:*+~@(),]")
_SENTENCE_END = re.compile(r"[a-zA-Z]{3,}[.?!]$")
_PSEUDO = re.compile(r"^[\w-]+:[\w-]+$")
_AT_RULE = re.compile(
    r"(?:^|\s)@(?:media|font-face|import|supports|keyframes|page)\b[^{}]*?(?=$|[A-ZÁÉÍÓÚÑ¿¡])"
)
_CSS_VALUE = re.compile(r"^[\d.]+(?:px|em|rem|%)?;?$")


def _selector_token(token: str) -> bool:
    lower = token.lower()
    if lower in _TAG_NAMES or lower in _MEDIA_WORDS:
        return True
    if _PSEUDO.match(lower) and not lower.startswith(("http:", "https:")):
        return True
    return bool(_SELECTOR_CHARS.search(token)) and not _SENTENCE_END.search(token)


def _trim_selector(prefix: str) -> str:
    parts = re.split(r"(\s+)", prefix)
    end = len(parts)
    while end > 0:
        token = parts[end - 1]
        if not token.strip():
            end -= 1
            continue
        if not _selector_token(token):
            break
        end -= 1
    return "".join(parts[:end])


def _looks_like_declarations(inner: str) -> bool:
    body = inner.strip()
    return not body or bool(_DECLARATIONS.match(body))


def strip_css_noise(value: str | None) -> str:
    """Remove CSS rules, @media blocks and stray braces from a text."""
    if not value:
        return ""
    text = _CSS_COMMENT.sub(" ", str(value))
    text = text.replace("<!--", " ").replace("-->", " ")
    if "{" not in text and "}" not in text:
        return re.sub(r"\s+", " ", text).strip()
    for _ in range(50):
        match = re.search(r"\{([^{}]*)\}", text)
        if not match:
            break
        before, after = text[: match.start()], text[match.end():]
        if _looks_like_declarations(match.group(1)):
            text = f"{_trim_selector(before)} {after}"
        else:
            text = f"{before} {match.group(1)} {after}"
    for _ in range(10):
        open_at = text.rfind("{")
        if open_at < 0:
            break
        rest = text[open_at + 1:]
        tokens = rest.split()
        css_rest = all(
            _selector_token(token)
            or ":" in token
            or ";" in token
            or _CSS_VALUE.match(token)
            or token.startswith("!important")
            for token in tokens
        )
        text = _trim_selector(text[:open_at]) if css_rest else f"{text[:open_at]} {rest}"
    text = _AT_RULE.sub(" ", text)
    text = text.replace("{", " ").replace("}", " ")
    text = re.sub(r"\s+", " ", text).strip()
    # Only selectors left after removing the rules ("body[data-x] .container-wide").
    rest = text.split()
    if rest and all(_selector_token(t) for t in rest) and any(re.search(r"[.#\[\]>]", t) for t in rest):
        return ""
    return text


def html_to_text(value: str | None) -> str:
    """Readable plain text from an HTML email body."""
    if not value:
        return ""
    text = _CONDITIONAL.sub(" ", str(value))
    text = _COMMENTS.sub(" ", text)
    text = _BLOCKS.sub(" ", text)
    text = _BREAKS.sub(" ", text)
    text = _TAGS.sub(" ", text)
    text = html.unescape(text).replace("\xa0", " ")
    return strip_css_noise(text)
