"""Vista previa del historial: muestra de remitentes/asuntos por proveedor.

Solo lectura en todos los proveedores (Gmail metadata, IMAP readonly +
BODY.PEEK, Graph $select). Nunca marca, mueve ni borra nada.
"""

from __future__ import annotations

import email
from datetime import datetime, timedelta, timezone
from email.header import decode_header, make_header
from typing import Any

from app.services.import_categories import summarize

SAMPLE_SIZE = 150


def _decode(value: str | None) -> str:
    try:
        return str(make_header(decode_header(value or "")))
    except Exception:
        return value or ""


def gmail_headers(credentials: Any, days: int, limit: int = SAMPLE_SIZE) -> list[tuple[str, str, list[str]]]:
    from app.services.gmail_import_inventory import EXCLUDED_QUERY, _service

    start = datetime.now(timezone.utc) - timedelta(days=days)
    service = _service(credentials)
    listing = service.users().messages().list(
        userId="me", q=f"after:{int(start.timestamp())} {EXCLUDED_QUERY}".strip(), maxResults=limit
    ).execute()
    out: list[tuple[str, str, list[str]]] = []

    def collect(_request_id: str, response: dict[str, Any] | None, exception: Exception | None) -> None:
        if exception or not response:
            return
        headers = {h.get("name", "").lower(): h.get("value", "") for h in (response.get("payload") or {}).get("headers") or []}
        out.append((headers.get("from", ""), headers.get("subject", ""), list(response.get("labelIds") or [])))

    batch = service.new_batch_http_request(callback=collect)
    for row in (listing.get("messages") or [])[:limit]:
        batch.add(service.users().messages().get(userId="me", id=row["id"], format="metadata", metadataHeaders=["From", "Subject"]))
    batch.execute()
    return out


def imap_headers(address: str, secret: str, *, oauth: bool, mailbox_provider: str, days: int, limit: int = SAMPLE_SIZE) -> list[tuple[str, str, list[str]]]:
    from app.services.yahoo_import import (
        _open_mailbox_client,
        _prepare_imap_secret,
        _select_folder,
        _uid_search,
        imap_search_date,
    )

    clean, prepared = _prepare_imap_secret(address, secret, oauth=oauth, mailbox_provider=mailbox_provider)
    client = _open_mailbox_client(clean, prepared, timeout=60, oauth=oauth, mailbox_provider=mailbox_provider)
    out: list[tuple[str, str, list[str]]] = []
    try:
        _select_folder(client, "INBOX", mailbox_provider)  # readonly=True
        since = datetime.now(timezone.utc) - timedelta(days=days)
        uids = _uid_search(client, "SINCE", imap_search_date(since))[-limit:]
        if uids:
            status, data = client.uid("FETCH", ",".join(uids), "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT)])")
            if status == "OK":
                for part in data or []:
                    if isinstance(part, tuple) and len(part) > 1:
                        parsed = email.message_from_bytes(part[1])
                        out.append((_decode(parsed.get("From")), _decode(parsed.get("Subject")), []))
    finally:
        try:
            client.logout()
        except Exception:
            pass
    return out


def microsoft_headers(account: dict[str, Any], days: int, limit: int = SAMPLE_SIZE) -> list[tuple[str, str, list[str]]]:
    from app.services.microsoft_import import (
        MICROSOFT_GRAPH_BASE,
        _graph_get_with_refresh,
        _graph_since,
        graph_address,
    )

    since = datetime.now(timezone.utc) - timedelta(days=days)
    payload = _graph_get_with_refresh(
        account,
        f"{MICROSOFT_GRAPH_BASE}/me/mailFolders/inbox/messages",
        params={
            "$select": "from,subject",
            "$top": str(min(limit, 999)),
            "$filter": f"receivedDateTime ge {_graph_since(since)}",
            "$orderby": "receivedDateTime desc",
        },
    )
    return [
        (graph_address(row.get("from")), str(row.get("subject") or ""), [])
        for row in payload.get("value") or []
        if isinstance(row, dict)
    ]


def build_preview(headers: list[tuple[str, str, list[str]]], eligible: int | None = None) -> dict[str, Any]:
    summary = summarize(headers)
    sampled = summary["sampled"]
    summary["eligible_messages"] = eligible
    # Estimación sobre el total: la muestra son los mensajes más recientes.
    summary["scale"] = (eligible / sampled) if eligible and sampled else 1.0
    return summary
