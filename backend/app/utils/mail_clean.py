"""Readable, de-noised text for one email (deterministic, stdlib only).

``clean_email`` turns the stored ``body_text`` / ``body_html`` of a message
into the few lines a person would actually read:

* HTML is converted to text keeping line structure (block elements end a
  line), so emails that only carry HTML (most banks and stores; 51 % of
  a real Yahoo mailbox) are readable even when ``body_text`` is a stub.
* Invisible "preheader" padding (U+034F, U+200B…, soft hyphen, U+2007…),
  encoding damage (UTF-8 read as Latin-1, "AtenciÃ³n"), ``[image: …]``
  placeholders, CSS leftovers and long tracking links are removed.
* Quoted reply history ("El … escribió:", "On … wrote:", Outlook headers,
  "> " lines), signatures ("Enviado desde Yahoo Mail") and footers / legal
  disclaimers (privacy notice, unsubscribe, "Este correo se constituye…")
  are cut.

The result is what ``mail_insights`` reads and what quotes are verified
against: every excerpt shown to the user must be a substring of ``text``.
Nothing here writes anywhere.
"""

from __future__ import annotations

import html
import re
import unicodedata
from dataclasses import dataclass, field
from email.header import decode_header, make_header

from app.utils.html_text import _drop_between, _drop_blocks, strip_css_noise

# Long hostile bodies are cut before any regex work (linear, bounded).
MAX_INPUT_CHARS = 400_000

_INVISIBLE = re.compile(
    "[\u00ad\u034f\u061c\u115f\u1160\u17b4\u17b5\u180e\u200b-\u200f"
    "\u202a-\u202e\u2060-\u2064\u2066-\u206f\ufeff\u3164\uffa0]"
)
# Figure/narrow/ideographic spaces used as padding become normal spaces.
_ODD_SPACES = re.compile("[\u00a0\u2000-\u200a\u2007\u202f\u205f\u3000]")
_SPACES = re.compile(r"[ \t\f\v]+")

# UTF-8 bytes decoded as cp1252/latin-1: "Ã©", "Ã³", "â€™", "Â¡".
_MOJIBAKE_RUN = re.compile(
    "(?:[\u00c2\u00c3\u00c5\u00e2][\u0080-\u00bf\u2018-\u201e\u2020-\u2022\u2026\u2030"
    "\u2039\u203a\u20ac\u2122\u0152\u0153\u0160\u0161\u0178\u017d\u017e\u0192\u02c6\u02dc]"
    "[\u0080-\u00bf\u2018-\u201e\u2020-\u2022\u2026\u2030\u2039\u203a\u20ac\u2122\u0153\u0161\u017e]?)+"
)

_BLOCK_BREAK = re.compile(
    r"<\s*(?:br|/p|/div|/tr|/li|/h[1-6]|/table|/blockquote|/center|/section|/header|/footer|hr|p|div|tr|li|h[1-6]|table)\b[^<>]*>",
    re.IGNORECASE,
)
_CELL_BREAK = re.compile(r"<\s*/?\s*(?:td|th)\b[^<>]*>", re.IGNORECASE)
_TAGS = re.compile(r"<[^<>]+>")

_PLACEHOLDER = re.compile(r"\[(?:image|imagen|imagem|immagine|cid|inline image)\s*:?[^\]\n]{0,300}\]", re.IGNORECASE)
_ANGLE_URL = re.compile(r"<\s*(?:https?://|mailto:)[^>\s]{0,2000}>", re.IGNORECASE)
_URL = re.compile(r"https?://[^\s<>\"')\]]+", re.IGNORECASE)

_QUOTE_HEADER = re.compile(
    r"^(?:el|on|le|il|em|am)\b.{3,240}?\b(?:escribi[oó]|wrote|a\s+[eé]crit|ha\s+scritto|escreveu|schrieb)\s*:?\s*$",
    re.IGNORECASE,
)
_ORIGINAL_SEPARATOR = re.compile(
    r"^-{2,}\s*(?:original message|mensaje original|message d'origine|messaggio originale|mensagem original)\s*-{0,}\s*$",
    re.IGNORECASE,
)
_OUTLOOK_FROM = re.compile(r"^\*?(?:de|from|von|da)\s*:\*?\s+\S", re.IGNORECASE)
_OUTLOOK_FIELD = re.compile(
    r"^\*?(?:enviado(?: el)?|sent|fecha|date|para|to|asunto|subject|envoy[eé]|inviato|cc)\s*:", re.IGNORECASE
)
_UNDERSCORE_RULE = re.compile(r"^_{8,}\s*$")

_SIGNATURE = re.compile(
    r"^(?:--\s*$|enviado desde (?:mi |el )?(?:yahoo|outlook|iphone|ipad|android|samsung|correo|gmail)"
    r"|sent from (?:my |yahoo|outlook|mail for)|yahoo mail: busca, organiza|obtener outlook para"
    r"|get outlook for|descargar outlook para|envoy[eé] de mon)",
    re.IGNORECASE,
)

_HEADER_JUNK = re.compile(
    r"^(?:si no puedes ver (?:este|el) (?:correo|mensaje).*|¿no puedes ver (?:este|el) (?:correo|mensaje).*"
    r"|ver (?:este |el )?(?:correo|mensaje) en (?:tu|el|su) navegador.*|ver versi[oó]n web.*"
    r"|view (?:this email |it )?in (?:your )?browser.*|having trouble viewing.*|haz clic aqu[ií]\.?"
    r"|click here\.?|no puedes visualizar.*|ver (?:online|en l[ií]nea)\s*(?:>|&gt;)?|view online\s*>?)$",
    re.IGNORECASE,
)

# A footer starts at the first line that is mostly one of these markers.
_FOOTER = re.compile(
    r"(?:aviso de privacidad|aviso legal|darte de baja|dar(?:se)? de baja|date de baja|cancelar (?:tu |la |su )?suscripci"
    r"|desuscrib|unsubscribe|opt[- ]out|pol[ií]tica de privacidad|privacy policy|privacy notice"
    r"|derechos reservados|all rights reserved|este correo se constituye|este (?:correo|mensaje)(?: electr[oó]nico)? (?:fue|ha sido|es) enviado"
    r"|este correo (?:electr[oó]nico )?es (?:generado|enviado) autom|no respondas (?:a )?este|no responda (?:a )?este|favor de no responder"
    r"|do not reply|please do not reply|no-?reply|administrar preferencias|preferencias de (?:e-?mail|correo)"
    r"|manage (?:your )?(?:email )?preferences|update your preferences|si no deseas recibir|si ya no deseas|you are receiving this"
    r"|you received this|recibes este correo|recibiste este correo|this email was sent|this message was sent"
    r"|protege tus datos|aviso de confidencialidad|confidentiality notice|este mensaje (?:y sus anexos )?(?:es|contiene|puede contener) (?:informaci[oó]n )?confidencial"
    r"|la informaci[oó]n contenida en este|the information contained in this|this (?:e-?mail|message)(?: and any attachments)? (?:is|may contain|contains) confidential"
    r"|s[ií]guenos en|follow us on|descarga (?:la|nuestra) app|t[eé]rminos y condiciones de uso)",
    re.IGNORECASE,
)

_SUBJECT_PREFIX = re.compile(r"^\s*(?:(?:re|rv|fw|fwd|tr|enc|aw|wg)\s*:\s*)+", re.IGNORECASE)

STUB_TEXT_CHARS = 80


@dataclass
class CleanEmail:
    """Cleaned body. ``text`` is the reference for exact quotes."""

    text: str
    lines: list[str]
    source: str  # "html" | "text" | "empty"
    removed: dict[str, int] = field(default_factory=dict)


def repair_mojibake(value: str) -> str:
    """Undo UTF-8 read as cp1252/latin-1 ("AtenciÃ³n" -> "Atención")."""

    def fix(match: re.Match[str]) -> str:
        chunk = match.group(0)
        for codec in ("cp1252", "latin-1"):
            try:
                repaired = chunk.encode(codec).decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue
            if repaired and len(repaired) < len(chunk):
                return repaired
        return chunk

    if not value or not _MOJIBAKE_RUN.search(value):
        return value
    return _MOJIBAKE_RUN.sub(fix, value)


def normalize_text(value: str | None) -> str:
    """NFC, no invisible padding, no encoding damage, single spaces per line."""
    if not value:
        return ""
    text = unicodedata.normalize("NFC", repair_mojibake(str(value)))
    text = _INVISIBLE.sub("", text)
    text = _ODD_SPACES.sub(" ", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(_SPACES.sub(" ", line).strip() for line in text.split("\n"))


def clean_subject(subject: str | None) -> str:
    """Decoded, normalised subject (broken RFC 2047 words, mojibake, padding)."""
    value = str(subject or "")
    if "=?" in value:
        try:
            value = str(make_header(decode_header(value)))
        except Exception:
            pass
    return " ".join(normalize_text(value).split())


def html_to_lines(value: str | None) -> list[str]:
    """Text lines from an HTML body; block elements end a line."""
    if not value:
        return []
    text = str(value)[:MAX_INPUT_CHARS]
    text = _drop_between(text, "<![if", "<![endif]>")
    text = _drop_between(text, "<!--", "-->")
    text = _drop_blocks(text)
    text = _BLOCK_BREAK.sub("\n", text)
    text = _CELL_BREAK.sub(" ", text)
    text = _TAGS.sub(" ", text)
    text = html.unescape(text)
    lines: list[str] = []
    for raw in normalize_text(text).split("\n"):
        line = strip_css_noise(raw) if ("{" in raw or "}" in raw or "/*" in raw) else raw
        line = line.strip()
        if line:
            lines.append(line)
    return lines


def html_to_readable_text(value: str | None) -> str:
    """Full readable text of an HTML body (for ``body_text`` at import)."""
    return "\n".join(html_to_lines(value))


def is_stub_text(text: str | None, subject: str | None = None) -> bool:
    """True when a plain-text part carries no real content.

    Yahoo/iCloud store the subject (or a 280-char snippet) when the email has
    no text/plain part; some senders put only "view in browser" in it."""
    value = " ".join(normalize_text(text).split())
    if len(value) < STUB_TEXT_CHARS:
        return True
    if subject and value.lower() == clean_subject(subject).lower():
        return True
    return False


def _shorten_url(match: re.Match[str]) -> str:
    url = match.group(0)
    if len(url) <= 50 and "?" not in url:
        return url
    host = re.sub(r"^https?://", "", url, flags=re.IGNORECASE).split("/")[0].split("?")[0]
    return host


def _cut_quoted(lines: list[str], removed: dict[str, int]) -> list[str]:
    kept: list[str] = []
    for index, line in enumerate(lines):
        if line.startswith(">"):
            removed["quoted"] = removed.get("quoted", 0) + 1
            continue
        joined = f"{line} {lines[index + 1]}" if index + 1 < len(lines) else line
        header = (
            _QUOTE_HEADER.match(line)
            or (len(line) < 200 and not line.endswith((".", "!", "?")) and _QUOTE_HEADER.match(joined))
            or _ORIGINAL_SEPARATOR.match(line)
        )
        outlook = False
        if not header and (_OUTLOOK_FROM.match(line) or _UNDERSCORE_RULE.match(line)):
            window = lines[index + 1:index + 5]
            outlook = sum(1 for item in window if _OUTLOOK_FIELD.match(item)) >= 2
        if (header or outlook) and kept:
            removed["quoted"] = removed.get("quoted", 0) + len(lines) - index
            return kept
        kept.append(line)
    return kept


def _cut_signature(lines: list[str], removed: dict[str, int]) -> list[str]:
    for index, line in enumerate(lines):
        if index > 0 and _SIGNATURE.match(line):
            removed["signature"] = removed.get("signature", 0) + len(lines) - index
            return lines[:index]
    return lines


_FOOTER_START = re.compile(
    r"^(?:¿necesitas (?:m[aá]s )?(?:ayuda|informaci[oó]n)\??|cont[aá]ctanos\b|cont[aá]ctenos\b|contact us\b|need help\?)",
    re.IGNORECASE,
)


def _cut_footer(lines: list[str], removed: dict[str, int]) -> list[str]:
    for index, line in enumerate(lines):
        if index > 0 and _FOOTER_START.match(line):
            removed["footer"] = removed.get("footer", 0) + len(lines) - index
            return lines[:index]
        if index == 0 or not _FOOTER.search(line):
            continue
        # Keep the line when the marker is a small part of a long content line.
        marker = _FOOTER.search(line)
        if marker and len(line) > 220 and marker.start() > 160:
            continue
        removed["footer"] = removed.get("footer", 0) + len(lines) - index
        return lines[:index]
    return lines


def clean_email(
    text: str | None,
    html_body: str | None = None,
    subject: str | None = None,
) -> CleanEmail:
    """Cleaned, readable lines of one email (see module docstring)."""
    removed: dict[str, int] = {}
    plain = str(text or "")[:MAX_INPUT_CHARS]
    if html_body and is_stub_text(plain, subject):
        lines = html_to_lines(html_body)
        source = "html"
    else:
        lines = normalize_text(plain).split("\n")
        source = "text"
    if not any(line.strip() for line in lines):
        if html_body and source == "text":
            lines, source = html_to_lines(html_body), "html"
    cleaned: list[str] = []
    for line in lines:
        value = line
        if _PLACEHOLDER.search(value):
            removed["placeholders"] = removed.get("placeholders", 0) + 1
            value = _PLACEHOLDER.sub(" ", value)
        if "http" in value.lower() or "mailto:" in value.lower():
            before = value
            value = _ANGLE_URL.sub(" ", value)
            value = _URL.sub(_shorten_url, value)
            if value != before:
                removed["links"] = removed.get("links", 0) + 1
        if "{" in value or "}" in value:
            value = strip_css_noise(value)
        value = _SPACES.sub(" ", value).strip(" \t|·•")
        if not value:
            continue
        if _HEADER_JUNK.match(value):
            removed["header"] = removed.get("header", 0) + 1
            continue
        if cleaned and cleaned[-1] == value:
            continue
        cleaned.append(value)
    cleaned = _cut_quoted(cleaned, removed)
    cleaned = _cut_signature(cleaned, removed)
    cleaned = _cut_footer(cleaned, removed)
    cleaned = _join_lines(cleaned)
    if not cleaned:
        source = "empty" if not (plain.strip() or html_body) else source
    return CleanEmail(text="\n".join(cleaned), lines=cleaned, source=source, removed=removed)


# Table/label layouts put "Monto de rechazo:" and "$751.28" on separate lines.
_LABEL_WORDS = re.compile(
    r"^(?:importe|monto|total|saldo|concepto|beneficiario|referencia|clave de rastreo|fecha(?: y hora)?|hora|operaci[oó]n"
    r"|comisi[oó]n\*?|tarjeta|cuenta|establecimiento|comercio|folio|de|para|amount|date|reference|merchant|from|to)$",
    re.IGNORECASE,
)
_ENDS_SENTENCE = re.compile(r"[.!?:;…»”\"')\]]$")


def _is_label(line: str) -> bool:
    if len(line) > 32 or re.search(r"\d", line):
        return False
    return line.endswith(":") or bool(_LABEL_WORDS.match(line))


def _join_lines(lines: list[str]) -> list[str]:
    """Re-join label/value pairs and hard-wrapped sentences.

    Only whitespace changes: the joined line is the two original lines with a
    single space between them, so quotes stay faithful to the email."""
    out: list[str] = []
    for line in lines:
        if out:
            previous = out[-1]
            label_pair = _is_label(previous) and not _is_label(line) and len(line) <= 100
            wrapped = (
                not _ENDS_SENTENCE.search(previous)
                and not _is_label(previous)
                and line[:1].islower()
                and len(previous) + len(line) < 600
            )
            if label_pair or wrapped:
                out[-1] = f"{previous} {line}"
                continue
        out.append(line)
    return out


def preview_text(clean: CleanEmail, limit: int = 280) -> str:
    """One-line preview (snippet) from cleaned lines."""
    return " ".join(" ".join(clean.lines).split())[:limit].strip()


def strip_subject_prefix(subject: str) -> str:
    return _SUBJECT_PREFIX.sub("", subject or "").strip()


def import_body(
    body_text: str | None,
    body_html: str | None,
    subject: str | None,
    snippet: str | None = None,
) -> tuple[str, str]:
    """``(body_text, snippet)`` to store for a newly imported message.

    Emails without a real text/plain part used to be stored with the subject
    as body (Yahoo/iCloud) or with the provider snippet (Gmail), so nothing
    downstream could read them. Now the HTML is converted to readable text
    and the snippet comes from the cleaned text, without invisible padding.
    """
    text = str(body_text or "")
    if body_html and is_stub_text(text, subject):
        readable = html_to_readable_text(body_html)
        if len(readable) > len(text.strip()):
            text = readable
    preview = preview_text(clean_email(text, body_html, subject))
    if not preview:
        preview = " ".join(normalize_text(snippet).split()) or " ".join(normalize_text(subject).split())
    if not text.strip():
        text = preview
    return text, preview[:280]
