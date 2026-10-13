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


GMAIL_SCAN_CAP = 1500          # más elegibles → muestra uniforme + extrapolación
_BATCH = 20                    # solicitudes por lote HTTP (concurrencia efectiva)
_MIN_BATCH_INTERVAL = 1.6      # s entre lotes: ~12.5 get/s = 250 unidades/s por usuario
_MAX_ATTEMPTS = 5
_DEADLINE_SECONDS = 150.0
CACHE_TTL = 1800.0
_HEADER_NAMES = ["From", "Subject", "List-Id", "List-Unsubscribe"]
# Respuesta parcial: solo etiquetas y las cabeceras pedidas; nunca cuerpo ni adjuntos.
_FIELDS = "labelIds,payload/headers"

# Caché en memoria del proceso. Clave = (workspace, cuenta conectada, días).
# Solo guarda agregados (conteos por categoría/esfera/red) y, como mucho, 3
# nombres de remitentes masivos por área. Nunca asuntos, ids ni contenido.
_CACHE: dict[tuple[str, str, int], tuple[float, dict[str, Any]]] = {}
_CACHE_ALLOWED = {"sampled", "categories", "spheres", "social_platforms", "examples",
                  "eligible_messages", "scale", "exact", "partial", "coverage", "history_days"}


def cache_key(workspace_id: str, account_id: str, days: int) -> tuple[str, str, int] | None:
    if not workspace_id or not account_id:
        return None  # sin identidad clara no se cachea
    return (str(workspace_id), str(account_id), int(days))


def cache_get(key: tuple[str, str, int] | None, now: float | None = None) -> dict[str, Any] | None:
    import time

    if key is None:
        return None
    hit = _CACHE.get(key)
    current = time.time() if now is None else now
    if hit and current - hit[0] < CACHE_TTL:
        return dict(hit[1])
    _CACHE.pop(key, None)
    return None


def cache_put(key: tuple[str, str, int] | None, value: dict[str, Any], now: float | None = None) -> None:
    import time

    if key is None:
        return
    current = time.time() if now is None else now
    for stale in [k for k, (t, _) in _CACHE.items() if current - t >= CACHE_TTL]:
        _CACHE.pop(stale, None)
    _CACHE[key] = (current, {k: v for k, v in value.items() if k in _CACHE_ALLOWED})


def cache_drop_account(workspace_id: str, account_id: str) -> None:
    for key in [k for k in _CACHE if k[0] == str(workspace_id) and k[1] == str(account_id)]:
        _CACHE.pop(key, None)


def _labels_with_list_hint(headers: dict[str, str], labels: list[str]) -> list[str]:
    out = list(labels)
    if headers.get("list-id") or headers.get("list-unsubscribe"):
        out.append("HAS_LIST_HEADERS")
    return out


def _retryable(exception: Exception) -> bool:
    """429, 5xx y 403 por cuota se reintentan; 400/401/403/404 permanentes no."""
    resp = getattr(exception, "resp", None)
    status = int(getattr(resp, "status", 0) or 0)
    if status == 0:
        return True  # red / timeout
    if status == 429 or status >= 500:
        return True
    if status == 403:
        text = str(getattr(exception, "content", b"") or b"")
        return "rateLimitExceeded" in text or "userRateLimitExceeded" in text
    return False


def _backoff(attempt: int) -> float:
    import random

    return min(16.0, 0.5 * (2 ** attempt)) * (0.5 + random.random())


def gmail_list_ids(service: Any, query: str, cap: int = GMAIL_SCAN_CAP) -> tuple[list[str], int]:
    """Todos los ids elegibles (paginado). Si hay más que `cap`, muestra uniforme."""
    import random

    ids: list[str] = []
    token: str | None = None
    while True:
        kwargs: dict[str, Any] = {"userId": "me", "q": query, "maxResults": 500, "fields": "messages/id,nextPageToken"}
        if token:
            kwargs["pageToken"] = token
        page = service.users().messages().list(**kwargs).execute()
        ids.extend(row["id"] for row in page.get("messages") or [] if row.get("id"))
        token = page.get("nextPageToken")
        if not token or len(ids) >= 20000:
            break
    total = len(ids)
    if total > cap:
        rng = random.Random(total)
        ids = sorted(rng.sample(ids, cap), key=ids.index)
    return ids, total


def gmail_headers(
    credentials: Any,
    days: int,
    limit: int = GMAIL_SCAN_CAP,
    stats: dict[str, Any] | None = None,
    *,
    sleep: Any = None,
    clock: Any = None,
) -> list[tuple[str, str, list[str]]]:
    """Solo metadatos (From, Subject, List-*, etiquetas). Nunca pide cuerpos."""
    import time

    from app.services.gmail_import_inventory import EXCLUDED_QUERY, _service

    sleep = sleep or time.sleep
    clock = clock or time.monotonic
    started = clock()
    start = datetime.now(timezone.utc) - timedelta(days=days)
    service = _service(credentials)
    ids, total = gmail_list_ids(service, f"after:{int(start.timestamp())} {EXCLUDED_QUERY}".strip(), limit)
    out: dict[str, tuple[str, str, list[str]]] = {}
    permanent: set[str] = set()
    pending = list(ids)
    last_batch = -1e9
    timed_out = False
    for attempt in range(_MAX_ATTEMPTS):
        retry: list[str] = []

        def collect(request_id: str, response: dict[str, Any] | None, exception: Exception | None) -> None:
            if exception is not None:
                if _retryable(exception):
                    retry.append(request_id)
                else:
                    permanent.add(request_id)
                return
            if not response:
                permanent.add(request_id)
                return
            headers = {h.get("name", "").lower(): h.get("value", "") for h in (response.get("payload") or {}).get("headers") or []}
            labels = _labels_with_list_hint(headers, list(response.get("labelIds") or []))
            out[request_id] = (headers.get("from", ""), headers.get("subject", ""), labels)

        for i in range(0, len(pending), _BATCH):
            if clock() - started > _DEADLINE_SECONDS:
                timed_out = True
                retry.extend(pending[i:])
                break
            wait = _MIN_BATCH_INTERVAL - (clock() - last_batch)
            if wait > 0:
                sleep(wait)
            last_batch = clock()
            batch = service.new_batch_http_request(callback=collect)
            for mid in pending[i:i + _BATCH]:
                batch.add(
                    service.users().messages().get(
                        userId="me", id=mid, format="metadata", metadataHeaders=_HEADER_NAMES, fields=_FIELDS
                    ),
                    request_id=mid,
                )
            try:
                batch.execute()
            except Exception as error:
                if _retryable(error):
                    retry.extend(pending[i:i + _BATCH])
                else:
                    raise
        pending = [mid for mid in dict.fromkeys(retry) if mid not in out and mid not in permanent]
        if not pending or timed_out:
            break
        sleep(_backoff(attempt))
    if stats is not None:
        stats["total"] = total
        stats["listed"] = len(ids)
        stats["failed"] = len(pending) + len(permanent)
        stats["timed_out"] = timed_out
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
    summary["coverage"] = round(sampled / eligible, 3) if eligible else (1.0 if sampled else 0.0)
    return summary
