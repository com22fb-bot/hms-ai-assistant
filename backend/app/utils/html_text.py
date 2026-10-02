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

# All patterns are bounded / non-overlapping so hostile mail (thousands of
# unclosed "<script" or "<!--") stays linear; block removal is a manual scan.
_BLOCK_OPEN = re.compile(r"<(head|style|script|noscript|title|xml)\b[^<>]*>", re.IGNORECASE)
# "[^<>]" stops at the next "<", so each failed attempt is bounded by the next
# tag start: linear overall, with no length cap (base64 src / long style attrs).
_BREAKS = re.compile(r"<\s*(?:br|/p|/div|/tr|/li|/h[1-6])\b[^<>]*>", re.IGNORECASE)
_TAGS = re.compile(r"<[^<>]+>")

_TAG_NAMES = {
    "html", "body", "table", "tbody", "thead", "tfoot", "tr", "td", "th", "div", "span", "p",
    "a", "img", "ul", "ol", "li", "h1", "h2", "h3", "h4", "h5", "h6", "center", "font", "b",
    "i", "u", "strong", "em", "section", "header", "footer", "main", "article", "nav", "sup",
    "sub", "hr", "br", "blockquote", "pre", "code", "input", "button", "form", "label", "o",
    "v", "*",
}
_MEDIA_WORDS = {"only", "screen", "and", "not", "print", "all", "speech", "or", ">", "+", "~", ","}
# Unambiguous (declarations separated by ";") to avoid catastrophic backtracking.
_DECLARATIONS = re.compile(r"^\s*[-\w]+\s*:[^;{}]*(?:;\s*[-\w]+\s*:[^;{}]*)*;?\s*$")
_SELECTOR_CHARS = re.compile(r"[.#\[\]>:*+~@(),]")
_SENTENCE_END = re.compile(r"[a-zA-Z]{3,}[.?!]$")
_PSEUDO = re.compile(r"^[\w-]+:[\w-]+$")
_AT_RULE = re.compile(
    r"(?:^|\s)@(?:media|font-face|import|supports|keyframes|page)\b[^{}]{0,300}?(?=$|[A-ZÁÉÍÓÚÑ¿¡])"
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


def _drop_between(text: str, opener: str, closer: str) -> str:
    """Remove every opener…closer span (case-insensitive) in one linear pass.

    An unclosed opener drops the rest of the text (it was never visible)."""
    lower = text.lower()
    out: list[str] = []
    pos = 0
    while True:
        start = lower.find(opener, pos)
        if start < 0:
            out.append(text[pos:])
            break
        out.append(text[pos:start])
        out.append(" ")
        end = lower.find(closer, start + len(opener))
        if end < 0:
            break
        pos = end + len(closer)
    return "".join(out)


def _drop_blocks(text: str) -> str:
    """Drop <head>/<style>/<script>/… elements with their content, linearly."""
    lower = text.lower()
    out: list[str] = []
    pos = 0
    unclosed: set[str] = set()  # no closer after an earlier opener => none after later ones
    while True:
        match = _BLOCK_OPEN.search(text, pos)
        if not match:
            out.append(text[pos:])
            break
        out.append(text[pos:match.start()])
        out.append(" ")
        tag = match.group(1).lower()
        end = -1 if tag in unclosed else lower.find(f"</{tag}", match.end())
        if end < 0:
            unclosed.add(tag)
            if tag == "head":
                # </head> is optional in HTML5: the head ends where <body> starts.
                body = lower.find("<body", match.end())
                pos = body if body >= 0 else match.end()
            else:
                # Unclosed element: drop only the opener; CSS leftovers are cleaned later.
                pos = match.end()
            continue
        close_end = lower.find(">", end)
        pos = len(text) if close_end < 0 else close_end + 1
    return "".join(out)


def strip_css_noise(value: str | None) -> str:
    """Remove CSS rules, @media blocks and stray braces from a text."""
    if not value:
        return ""
    text = _drop_between(str(value), "/*", "*/")
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
    text = _drop_between(str(value), "<![if", "<![endif]>")
    text = _drop_between(text, "<!--", "-->")
    text = _drop_blocks(text)
    text = _BREAKS.sub(" ", text)
    text = _TAGS.sub(" ", text)
    text = html.unescape(text).replace("\xa0", " ")
    return strip_css_noise(text)
