"""Lectura de Yahoo Mail por IMAP (contraseña de aplicación)."""

from __future__ import annotations

import email
import imaplib
import re
from email.header import decode_header, make_header
from email.utils import parseaddr, parsedate_to_datetime
from typing import Any


YAHOO_IMAP_HOST = "imap.mail.yahoo.com"
YAHOO_IMAP_PORT = 993


class YahooImapError(RuntimeError):
    """Fallo al conectar o leer Yahoo IMAP."""


def _decode_header_value(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value or ""


def verify_yahoo_login(address: str, app_password: str) -> None:
    """Comprueba usuario/contraseña de aplicación contra Yahoo IMAP."""
    address = address.strip().lower()
    app_password = app_password.strip().replace(" ", "")
    if not address or "@" not in address:
        raise YahooImapError("El correo de Yahoo no es válido.")
    if len(app_password) < 8:
        raise YahooImapError(
            "Usa la contraseña de aplicación de Yahoo "
            "(no la contraseña normal de la cuenta)."
        )

    try:
        client = imaplib.IMAP4_SSL(YAHOO_IMAP_HOST, YAHOO_IMAP_PORT)
        try:
            status, _ = client.login(address, app_password)
            if status != "OK":
                raise YahooImapError(
                    "Yahoo rechazó el acceso. Revisa el correo y la "
                    "contraseña de aplicación."
                )
        finally:
            try:
                client.logout()
            except Exception:
                pass
    except YahooImapError:
        raise
    except imaplib.IMAP4.error as error:
        raise YahooImapError(
            "Yahoo rechazó el acceso IMAP. "
            "Casi siempre falta la contraseña de aplicación: "
            "Security → External connections → Create app password → "
            "nombre Donexto → copia el código de 16 caracteres "
            "(no uses la contraseña normal de Yahoo ni la de Donexto)."
        ) from error
    except Exception as error:
        raise YahooImapError(
            f"Error de red al conectar con Yahoo: {error}"
        ) from error


def list_yahoo_messages(
    address: str,
    app_password: str,
    *,
    max_results: int = 20,
) -> list[dict[str, Any]]:
    """Lista mensajes recientes del INBOX de Yahoo."""
    address = address.strip().lower()
    app_password = app_password.strip().replace(" ", "")
    max_results = max(1, min(int(max_results), 100))

    messages: list[dict[str, Any]] = []

    try:
        client = imaplib.IMAP4_SSL(YAHOO_IMAP_HOST, YAHOO_IMAP_PORT)
        try:
            status, _ = client.login(address, app_password)
            if status != "OK":
                raise YahooImapError("Yahoo rechazó el acceso IMAP.")

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
                snippet = subject or "(sin vista previa)"
                snippet = re.sub(r"\s+", " ", snippet).strip()[:280]

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
