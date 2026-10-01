"""Lectura de Yahoo Mail por IMAP con OAuth (el usuario firma en Yahoo)."""

from __future__ import annotations

import email
import imaplib
import re
import socket
from datetime import datetime, timezone
from typing import Any

from app.services.imap_mail import (
    ImapMailError,
    decode_header_value,
    list_inbox_messages,
    open_imap_client,
)
from app.services.imap_provider import YAHOO_IMAP
from app.services.yahoo_domains import is_yahoo_mail_address

YAHOO_IMAP_HOST = YAHOO_IMAP.host
YAHOO_IMAP_PORT = YAHOO_IMAP.port


class YahooImapError(RuntimeError):
    """Fallo al conectar o leer Yahoo IMAP."""


def stored_yahoo_uses_oauth(stored: dict[str, Any] | None) -> bool:
    if not stored:
        return False
    metadata = stored.get("metadata") or {}
    if not isinstance(metadata, dict):
        return False
    return str(metadata.get("auth") or "").lower() in {
        "oauthbearer",
        "oauth",
        "oauth2",
    }


def _decode_header_value(value: str | None) -> str:
    return decode_header_value(value)


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
    return is_yahoo_mail_address(address)


_YAHOO_OAUTH_BLOCKED = (
    "Donexto aún no puede leer este buzón Yahoo. "
    "Falta el permiso de correo que Yahoo aprueba en la app. "
    "No hace falta volver a firmar."
)


def _open_yahoo_client(
    address: str,
    app_password: str,
    *,
    timeout: int = 45,
    oauth: bool = False,
) -> imaplib.IMAP4_SSL:
    try:
        return open_imap_client(
            YAHOO_IMAP,
            address,
            app_password,
            timeout=timeout,
            oauth=oauth,
        )
    except ImapMailError as error:
        raise YahooImapError(
            _YAHOO_OAUTH_BLOCKED
            if oauth or error.code == "oauth_rejected"
            else "Yahoo no aceptó esa clave. Escríbela igual que cuando entras a Yahoo."
        ) from error


def verify_yahoo_login(address: str, app_password: str) -> None:
    """Legacy: IMAP LOGIN. El producto ya no pide claves; no lo usa la API."""
    address = normalize_yahoo_address(address)
    app_password = normalize_yahoo_app_password(app_password)

    if not address or "@" not in address:
        raise YahooImapError("El correo de Yahoo no es válido.")

    if not _is_yahoo_like_address(address):
        raise YahooImapError(
            "Indica un correo de Yahoo (@yahoo.com, @yahoo.com.mx, "
            "@ymail.com, @rocketmail.com o similar)."
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
    oauth: bool = False,
) -> list[dict[str, Any]]:
    """Lista mensajes recientes del INBOX de Yahoo. Solo lectura."""
    address = normalize_yahoo_address(address)
    if not oauth:
        app_password = normalize_yahoo_app_password(app_password)
    try:
        return list_inbox_messages(
            YAHOO_IMAP,
            address,
            app_password,
            max_results=max_results,
            oauth=oauth,
            labels=["YAHOO", "INBOX"],
        )
    except YahooImapError:
        raise
    except ImapMailError as error:
        raise YahooImapError(str(error)) from error
    except Exception as error:
        raise YahooImapError(
            f"No fue posible leer correos de Yahoo: {error}"
        ) from error


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
