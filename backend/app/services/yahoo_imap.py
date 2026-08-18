"""Lectura de Yahoo Mail por IMAP (correo y clave de Yahoo)."""

from __future__ import annotations

import email
import imaplib
import re
import socket
import ssl
from datetime import datetime, timezone
from email.header import decode_header, make_header
from email.utils import parseaddr, parsedate_to_datetime
from typing import Any


YAHOO_IMAP_HOST = "imap.mail.yahoo.com"
YAHOO_IMAP_PORT = 993
YAHOO_DOMAINS = (
    "yahoo.com",
    "yahoo.com.mx",
    "yahoo.es",
    "ymail.com",
    "rocketmail.com",
)


class YahooImapError(RuntimeError):
    """Fallo al conectar o leer Yahoo IMAP."""


def _decode_header_value(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value or ""


def normalize_yahoo_address(address: str) -> str:
    return address.strip().lower()


def normalize_yahoo_app_password(raw: str) -> str:
    """
    Clave IMAP de Yahoo.

    La clave normal se respeta tal cual (símbolos, guiones, espacios).
    Solo se quitan espacios si el resto son exactamente 16 letras o
    números — el formato clásico de un código de aplicación.
    """
    cleaned = (raw or "").strip().replace("\u00a0", " ")
    no_spaces = re.sub(r"\s+", "", cleaned)
    if re.fullmatch(r"[A-Za-z0-9]{16}", no_spaces):
        return no_spaces
    return cleaned


def _is_yahoo_like_address(address: str) -> bool:
    if "@" not in address:
        return False
    domain = address.rsplit("@", 1)[-1]
    return any(
        domain == item or domain.endswith("." + item)
        for item in YAHOO_DOMAINS
    )


def _open_yahoo_client(
    address: str,
    app_password: str,
    *,
    timeout: int = 45,
) -> imaplib.IMAP4_SSL:
    context = ssl.create_default_context()
    safe_timeout = max(15, int(timeout))
    try:
        client = imaplib.IMAP4_SSL(
            YAHOO_IMAP_HOST,
            YAHOO_IMAP_PORT,
            ssl_context=context,
            timeout=safe_timeout,
        )
    except TypeError:
        # Python sin soporte timeout en este build
        socket.setdefaulttimeout(safe_timeout)
        client = imaplib.IMAP4_SSL(
            YAHOO_IMAP_HOST,
            YAHOO_IMAP_PORT,
            ssl_context=context,
        )

    status, _data = client.login(address, app_password)
    if status != "OK":
        try:
            client.logout()
        except Exception:
            pass
        raise YahooImapError(
            "Yahoo no aceptó esa clave. Escríbela igual que cuando entras a Yahoo."
        )
    return client


def verify_yahoo_login(address: str, app_password: str) -> None:
    """Comprueba correo y clave de Yahoo contra IMAP."""
    address = normalize_yahoo_address(address)
    app_password = normalize_yahoo_app_password(app_password)

    if not address or "@" not in address:
        raise YahooImapError("El correo de Yahoo no es válido.")

    if not _is_yahoo_like_address(address):
        raise YahooImapError(
            "Indica un correo de Yahoo (@yahoo.com, @ymail.com, "
            "@rocketmail.com o similar)."
        )

    if len(app_password) < 6:
        raise YahooImapError(
            "Esa clave es demasiado corta. Usa la misma con la que entras a Yahoo."
        )

    try:
        client = _open_yahoo_client(address, app_password)
        try:
            status, _ = client.select("INBOX", readonly=True)
            if status != "OK":
                raise YahooImapError(
                    "La contraseña es válida, pero no se pudo abrir el INBOX. "
                    "Revisa la cuenta Yahoo e inténtalo de nuevo."
                )
        finally:
            try:
                client.logout()
            except Exception:
                pass
    except YahooImapError:
        raise
    except imaplib.IMAP4.error as error:
        err = str(error).lower()
        if "invalid" in err or "login" in err or "auth" in err:
            raise YahooImapError(
                "Yahoo no aceptó el correo o la clave. "
                "Escríbelos igual que cuando entras a Yahoo."
            ) from error
        raise YahooImapError(
            f"Yahoo IMAP falló al autenticar: {error}"
        ) from error
    except (TimeoutError, socket.timeout, OSError) as error:
        raise YahooImapError(
            "No hubo respuesta de los servidores IMAP de Yahoo "
            f"(imap.mail.yahoo.com:993). Detalle de red: {error}"
        ) from error
    except Exception as error:
        raise YahooImapError(
            f"Error al conectar con Yahoo IMAP: {error}"
        ) from error


def list_yahoo_messages(
    address: str,
    app_password: str,
    *,
    max_results: int = 20,
) -> list[dict[str, Any]]:
    """Lista mensajes recientes del INBOX de Yahoo."""
    address = normalize_yahoo_address(address)
    app_password = normalize_yahoo_app_password(app_password)
    max_results = max(1, min(int(max_results), 100))
    messages: list[dict[str, Any]] = []

    try:
        client = _open_yahoo_client(address, app_password)
        try:
            status, _ = client.select("INBOX", readonly=True)
            if status != "OK":
                raise YahooImapError(
                    "No fue posible abrir el INBOX de Yahoo."
                )

            status, data = client.search(None, "ALL")
            if status != "OK" or not data or not data[0]:
                return []

            ids = data[0].split()
            selected = list(reversed(ids[-max_results:]))

            for raw_id in selected:
                msg_id = raw_id.decode("ascii", errors="ignore")
                status, fetched = client.fetch(
                    raw_id,
                    "(FLAGS BODY.PEEK[HEADER])",
                )
                if status != "OK" or not fetched:
                    continue

                header_bytes = b""
                flags_text = ""
                for part in fetched:
                    if isinstance(part, tuple) and len(part) >= 2:
                        meta = part[0]
                        payload = part[1]
                        if isinstance(meta, bytes):
                            flags_text += meta.decode(
                                "utf-8", errors="ignore"
                            )
                        elif isinstance(meta, str):
                            flags_text += meta
                        if isinstance(payload, bytes) and payload:
                            header_bytes = payload

                parsed = email.message_from_bytes(header_bytes or b"")
                subject = _decode_header_value(parsed.get("Subject"))
                from_raw = _decode_header_value(parsed.get("From"))
                to_raw = _decode_header_value(parsed.get("To"))
                date_raw = parsed.get("Date")
                sender_name, sender_email = parseaddr(from_raw)
                received_at = None
                if date_raw:
                    try:
                        received_at = parsedate_to_datetime(
                            date_raw
                        ).isoformat()
                    except Exception:
                        received_at = date_raw

                is_unread = "\\Seen" not in flags_text
                snippet = re.sub(
                    r"\s+", " ", subject or "(sin vista previa)"
                ).strip()[:280]

                messages.append(
                    {
                        "id": msg_id,
                        "thread_id": msg_id,
                        "subject": subject or "(sin asunto)",
                        "sender": sender_name or from_raw or "Desconocido",
                        "sender_email": sender_email or None,
                        "recipient": to_raw or None,
                        "received_at": received_at,
                        "snippet": snippet,
                        "is_unread": is_unread,
                        "labels": ["YAHOO", "INBOX"],
                    }
                )
        finally:
            try:
                client.logout()
            except Exception:
                pass
    except YahooImapError:
        raise
    except Exception as error:
        raise YahooImapError(
            f"No fue posible leer correos de Yahoo: {error}"
        ) from error

    return messages


IMAP_MONTHS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)

INBOX_ALIASES = {"inbox"}
SENT_ALIASES = {"sent", "sent mail", "sent messages", "sent items", "enviados"}
DRAFT_ALIASES = {"draft", "drafts", "borradores"}
SPAM_ALIASES = {"bulk mail", "junk", "spam", "correo no deseado"}
TRASH_ALIASES = {"trash", "deleted", "deleted items", "papelera"}


def imap_search_date(value: datetime) -> str:
    current = value.astimezone(timezone.utc) if value.tzinfo else value.replace(
        tzinfo=timezone.utc
    )
    return f"{current.day:02d}-{IMAP_MONTHS[current.month - 1]}-{current.year}"


def classify_yahoo_folder(name: str) -> str:
    lowered = name.strip().lower().strip('"')
    leaf = lowered.rsplit("/", 1)[-1].rsplit(".", 1)[-1]
    if leaf in INBOX_ALIASES or lowered in INBOX_ALIASES:
        return "inbox"
    if leaf in SENT_ALIASES or lowered in SENT_ALIASES:
        return "sent"
    if leaf in DRAFT_ALIASES or lowered in DRAFT_ALIASES:
        return "draft"
    if leaf in SPAM_ALIASES or lowered in SPAM_ALIASES:
        return "spam"
    if leaf in TRASH_ALIASES or lowered in TRASH_ALIASES:
        return "trash"
    return "other"


def parse_list_mailbox_name(raw: bytes | str) -> str | None:
    text = (
        raw.decode("utf-8", errors="ignore")
        if isinstance(raw, bytes)
        else str(raw)
    ).strip()
    if not text:
        return None
    quoted = re.findall(r'"((?:\\.|[^"\\])*)"', text)
    if quoted:
        return quoted[-1].replace('\\"', '"')
    parts = text.split()
    return parts[-1] if parts else None


def encode_yahoo_ref(folder: str, uid: str) -> str:
    return f"{folder}\x1f{uid}"


def decode_yahoo_ref(ref: str) -> tuple[str, str]:
    if "\x1f" in ref:
        folder, uid = ref.split("\x1f", 1)
        return folder, uid
    if ":" in ref:
        folder, uid = ref.split(":", 1)
        return folder, uid
    return "INBOX", ref


def extract_rfc822_bodies(parsed: email.message.Message) -> tuple[str, str, bool]:
    text = ""
    html = ""
    has_attachments = False

    if parsed.is_multipart():
        for part in parsed.walk():
            disposition = str(part.get("Content-Disposition") or "").lower()
            content_type = part.get_content_type()
            if "attachment" in disposition:
                has_attachments = True
                continue
            payload = part.get_payload(decode=True)
            if not isinstance(payload, (bytes, bytearray)):
                continue
            charset = part.get_content_charset() or "utf-8"
            try:
                decoded = payload.decode(charset, errors="replace")
            except LookupError:
                decoded = payload.decode("utf-8", errors="replace")
            if content_type == "text/plain" and not text:
                text = decoded
            elif content_type == "text/html" and not html:
                html = decoded
        return text, html, has_attachments

    payload = parsed.get_payload(decode=True)
    charset = parsed.get_content_charset() or "utf-8"
    if isinstance(payload, (bytes, bytearray)):
        try:
            decoded = payload.decode(charset, errors="replace")
        except LookupError:
            decoded = payload.decode("utf-8", errors="replace")
        if parsed.get_content_type() == "text/html":
            html = decoded
        else:
            text = decoded
    return text, html, has_attachments
