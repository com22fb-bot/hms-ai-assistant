"""Cliente IMAP de solo lectura, independiente del proveedor.

Abre el buzón con EXAMINE (`select(..., readonly=True)`) y descarga
con BODY.PEEK. No marca leído, no mueve y no borra.

El secreto (token OAuth o contraseña de app) no se escribe en logs.
"""

from __future__ import annotations

import email
import imaplib
import re
import socket
import ssl
from email.header import decode_header, make_header
from email.utils import parseaddr, parsedate_to_datetime
from typing import Any

from app.services.imap_provider import (
    PEEK_HEADER_SPEC,
    ImapProviderConfig,
)


class ImapMailError(RuntimeError):
    """Fallo al conectar o leer un buzón IMAP."""

    def __init__(self, message: str, *, code: str = "imap_failed") -> None:
        super().__init__(message)
        self.code = code


def scrub_secret(text: str, secret: str) -> str:
    """Quita el secreto si un mensaje de error lo arrastró."""
    cleaned = text or ""
    raw = (secret or "").strip()
    if raw and raw in cleaned:
        cleaned = cleaned.replace(raw, "[redacted]")
    compact = re.sub(r"[\s-]+", "", raw)
    if len(compact) >= 8 and compact in cleaned:
        cleaned = cleaned.replace(compact, "[redacted]")
    return cleaned


def decode_header_value(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value or ""


def normalize_imap_address(address: str) -> str:
    return (address or "").strip().lower()


def address_domain(address: str) -> str:
    clean = normalize_imap_address(address)
    at = clean.rfind("@")
    if at < 0:
        return ""
    return clean[at + 1 :]


def address_matches(config: ImapProviderConfig, address: str) -> bool:
    domain = address_domain(address)
    if not domain or not config.domains:
        return False
    return any(
        domain == root or domain.endswith("." + root) for root in config.domains
    )


def open_imap_client(
    config: ImapProviderConfig,
    address: str,
    secret: str,
    *,
    timeout: int = 45,
    oauth: bool = False,
) -> imaplib.IMAP4_SSL:
    """SSL + LOGIN o OAUTHBEARER. No registra el secreto."""
    context = ssl.create_default_context()
    safe_timeout = max(15, int(timeout))
    client: imaplib.IMAP4_SSL | None = None
    try:
        try:
            client = imaplib.IMAP4_SSL(
                config.host,
                config.port,
                ssl_context=context,
                timeout=safe_timeout,
            )
        except TypeError:
            socket.setdefaulttimeout(safe_timeout)
            client = imaplib.IMAP4_SSL(
                config.host,
                config.port,
                ssl_context=context,
            )

        if oauth:
            initial = (
                f"n,a={address},\x01host={config.host}\x01port={config.port}"
                f"\x01auth=Bearer {secret}\x01\x01"
            ).encode("utf-8")

            def _oauthbearer(_challenge: bytes | None) -> bytes:
                return initial

            try:
                status, _data = client.authenticate("OAUTHBEARER", _oauthbearer)
            except imaplib.IMAP4.error as error:
                _logout_quietly(client)
                raise ImapMailError(
                    scrub_secret(str(error), secret) or "IMAP OAuth rechazado.",
                    code="oauth_rejected",
                ) from error
        else:
            try:
                status, _data = client.login(address, secret)
            except imaplib.IMAP4.error as error:
                _logout_quietly(client)
                detail = scrub_secret(str(error), secret).strip()
                raise ImapMailError(
                    detail or f"{config.label} rechazó el acceso IMAP.",
                    code="auth_failed",
                ) from error
    except ImapMailError:
        raise
    except (TimeoutError, socket.timeout, ssl.SSLError, OSError) as error:
        if client is not None:
            _logout_quietly(client)
        detail = scrub_secret(str(error), secret).strip()
        raise ImapMailError(
            detail or f"No fue posible conectar con {config.label}.",
            code="network",
        ) from error

    if status != "OK":
        _logout_quietly(client)
        raise ImapMailError(
            f"{config.label} no aceptó el acceso IMAP.",
            code="auth_failed",
        )
    return client


def examine_mailbox(client: Any, mailbox: str = "INBOX") -> None:
    """EXAMINE: abre solo lectura. No cambia flags."""
    status, _ = client.select(mailbox, readonly=True)
    if status != "OK":
        raise ImapMailError(
            f"No fue posible abrir {mailbox} en solo lectura.",
            code="mailbox_unavailable",
        )


def _logout_quietly(client: Any) -> None:
    try:
        client.logout()
    except Exception:
        pass


def list_inbox_messages(
    config: ImapProviderConfig,
    address: str,
    secret: str,
    *,
    max_results: int = 20,
    oauth: bool = False,
    labels: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Encabezados recientes del INBOX. BODY.PEEK no marca leído."""
    max_results = max(1, min(int(max_results), 100))
    applied_labels = labels or [config.provider_id.upper(), "INBOX"]
    messages: list[dict[str, Any]] = []

    client = open_imap_client(
        config,
        address,
        secret,
        oauth=oauth,
    )
    try:
        examine_mailbox(client, "INBOX")
        status, data = client.search(None, "ALL")
        if status != "OK" or not data or not data[0]:
            return []

        ids = data[0].split()
        selected = list(reversed(ids[-max_results:]))
        for raw_id in selected:
            msg_id = raw_id.decode("ascii", errors="ignore")
            status, fetched = client.fetch(raw_id, PEEK_HEADER_SPEC)
            if status != "OK" or not fetched:
                continue

            header_bytes = b""
            flags_text = ""
            for part in fetched:
                if isinstance(part, tuple) and len(part) >= 2:
                    meta = part[0]
                    payload = part[1]
                    if isinstance(meta, bytes):
                        flags_text += meta.decode("utf-8", errors="ignore")
                    elif isinstance(meta, str):
                        flags_text += meta
                    if isinstance(payload, bytes) and payload:
                        header_bytes = payload

            parsed = email.message_from_bytes(header_bytes or b"")
            subject = decode_header_value(parsed.get("Subject"))
            from_raw = decode_header_value(parsed.get("From"))
            to_raw = decode_header_value(parsed.get("To"))
            date_raw = parsed.get("Date")
            sender_name, sender_email = parseaddr(from_raw)
            received_at = None
            if date_raw:
                try:
                    received_at = parsedate_to_datetime(date_raw).isoformat()
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
                    "labels": list(applied_labels),
                }
            )
    finally:
        _logout_quietly(client)

    return messages
