"""Lectura de Yahoo Mail por IMAP (contraseña de aplicación)."""

from __future__ import annotations

import email
import imaplib
import re
import socket
import ssl
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
    Normaliza contraseña de aplicación Yahoo.

    Yahoo genera ~16 caracteres alfanuméricos (a veces con espacios).
    El gestor de contraseñas a veces pega guiones o textos extra.
    """
    cleaned = raw.strip()
    # Quita etiquetas tipo "App password: "
    cleaned = re.sub(
        r"(?i)^(?:app\s*password|contrase[nñ]a(?:\s+de\s+aplicaci[oó]n)?)\s*[:=]?\s*",
        "",
        cleaned,
    ).strip()
    cleaned = cleaned.replace("\u00a0", " ")
    cleaned = cleaned.replace("-", " ").replace(".", " ")
    cleaned = re.sub(r"\s+", "", cleaned)
    # Solo caracteres alfanuméricos típicos de app password
    alnum = re.sub(r"[^A-Za-z0-9]", "", cleaned)
    if len(alnum) >= 12:
        return alnum
    return cleaned


def _is_yahoo_like_address(address: str) -> bool:
    if "@" not in address:
        return False
    domain = address.rsplit("@", 1)[-1]
    return any(
        domain == item or domain.endswith("." + item)
        for item in YAHOO_DOMAINS
    )


def _open_yahoo_client(address: str, app_password: str) -> imaplib.IMAP4_SSL:
    context = ssl.create_default_context()
    try:
        client = imaplib.IMAP4_SSL(
            YAHOO_IMAP_HOST,
            YAHOO_IMAP_PORT,
            ssl_context=context,
            timeout=45,
        )
    except TypeError:
        # Python sin soporte timeout en este build
        socket.setdefaulttimeout(45)
        client = imaplib.IMAP4_SSL(
            YAHOO_IMAP_HOST,
            YAHOO_IMAP_PORT,
            ssl_context=context,
        )

    status, data = client.login(address, app_password)
    if status != "OK":
        try:
            client.logout()
        except Exception:
            pass
        detail = ""
        if data:
            detail = " ".join(
                part.decode("utf-8", errors="ignore")
                if isinstance(part, bytes)
                else str(part)
                for part in data
            )
        raise YahooImapError(
            "Yahoo rechazó el acceso IMAP"
            + (f" ({detail.strip()})" if detail.strip() else "")
            + ". Usa una contraseña de aplicación nueva."
        )
    return client


def verify_yahoo_login(address: str, app_password: str) -> None:
    """Comprueba usuario/contraseña de aplicación contra Yahoo IMAP."""
    address = normalize_yahoo_address(address)
    app_password = normalize_yahoo_app_password(app_password)

    if not address or "@" not in address:
        raise YahooImapError("El correo de Yahoo no es válido.")

    if not _is_yahoo_like_address(address):
        raise YahooImapError(
            "Indica un correo de Yahoo (@yahoo.com, @ymail.com, "
            "@rocketmail.com o similar)."
        )

    if len(app_password) < 12:
        raise YahooImapError(
            "La contraseña de aplicación es demasiado corta. "
            "En Yahoo genera una en Seguridad → Conexiones externas → "
            "Crear contraseña de aplicación (código de ~16 caracteres)."
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
                "Yahoo rechazó usuario o contraseña. "
                "Genera una contraseña de aplicación nueva (no la de "
                "mail.yahoo.com ni la de Donexto) y pégala sin espacios."
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
