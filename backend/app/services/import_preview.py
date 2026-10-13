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

SAMPLE_SIZE = 1000


def _decode(value: str | None) -> str:
    try:
        return str(make_header(decode_header(value or "")))
    except Exception:
        return value or ""


GMAIL_SCAN_CAP = 3000
_BATCH = 40
_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
CACHE_TTL = 1800.0
_HEADER_NAMES = ["From", "Subject", "List-Id", "List-Unsubscribe"]


def cache_get(key: str) -> dict[str, Any] | None:
    import time

    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < CACHE_TTL:
        return hit[1]
    return None


def cache_put(key: str, value: dict[str, Any]) -> None:
    import time

    if len(_CACHE) > 500:
        _CACHE.clear()
    _CACHE[key] = (time.time(), value)


def _labels_with_list_hint(headers: dict[str, str], labels: list[str]) -> list[str]:
    out = list(labels)
    if headers.get("list-id") or headers.get("list-unsubscribe"):
        out.append("HAS_LIST_HEADERS")
    return out


def gmail_list_ids(service: Any, query: str, cap: int = GMAIL_SCAN_CAP) -> tuple[list[str], int]:
    """Todos los ids elegibles (paginado) hasta `cap`; devuelve (ids, total_estimado)."""
    ids: list[str] = []
    token: str | None = None
    estimate = 0
    while True:
        kwargs: dict[str, Any] = {"userId": "me", "q": query, "maxResults": 500}
        if token:
            kwargs["pageToken"] = token
        page = service.users().messages().list(**kwargs).execute()
        ids.extend(row["id"] for row in page.get("messages") or [] if row.get("id"))
        token = page.get("nextPageToken")
        estimate = max(estimate, len(ids))
        if not token:
            break
        if len(ids) >= cap:
            estimate = max(estimate, int(page.get("resultSizeEstimate") or 0) + len(ids))
            break
    return ids[:cap], estimate


def gmail_headers(credentials: Any, days: int, limit: int = GMAIL_SCAN_CAP, stats: dict[str, Any] | None = None) -> list[tuple[str, str, list[str]]]:
    """Solo metadatos (From, Subject, List-*, etiquetas). Nunca pide cuerpos."""
    import time

    from app.services.gmail_import_inventory import EXCLUDED_QUERY, _service

    start = datetime.now(timezone.utc) - timedelta(days=days)
    service = _service(credentials)
    ids, total = gmail_list_ids(service, f"after:{int(start.timestamp())} {EXCLUDED_QUERY}".strip(), limit)
    out: dict[str, tuple[str, str, list[str]]] = {}
    pending = list(ids)
    for attempt in range(4):
        failed: list[str] = []

        def collect(request_id: str, response: dict[str, Any] | None, exception: Exception | None) -> None:
            if exception or not response:
                failed.append(request_id)
                return
            headers = {h.get("name", "").lower(): h.get("value", "") for h in (response.get("payload") or {}).get("headers") or []}
            labels = _labels_with_list_hint(headers, list(response.get("labelIds") or []))
            out[request_id] = (headers.get("from", ""), headers.get("subject", ""), labels)

        for i in range(0, len(pending), _BATCH):
            batch = service.new_batch_http_request(callback=collect)
            for mid in pending[i:i + _BATCH]:
                batch.add(
                    service.users().messages().get(userId="me", id=mid, format="metadata", metadataHeaders=_HEADER_NAMES),
                    request_id=mid,
                )
            try:
                batch.execute()
            except Exception:
                failed.extend(pending[i:i + _BATCH])
        pending = [mid for mid in failed if mid not in out]
        if not pending:
            break
        time.sleep(0.5 * (attempt + 1))
    if stats is not None:
        stats["total"] = total
        stats["listed"] = len(ids)
        stats["failed"] = len(pending)
    return list(out.values())


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
    summary["scale"] = (eligible / sampled) if eligible and sampled and eligible > sampled else 1.0
    summary["exact"] = summary["scale"] == 1.0
    return summary
