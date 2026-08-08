from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.security.identity import require_google_account
from app.services.oauth_storage import OAuthStorage


TRIAGE_CATEGORIES = {
    "unreviewed",
    "action_required",
    "waiting_external",
    "review",
    "notice",
    "informational",
    "automated",
    "promotional",
    "social",
}


def _rows(response: Any) -> list[dict[str, Any]]:
    data = getattr(response, "data", None)
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def _first(response: Any) -> dict[str, Any] | None:
    rows = _rows(response)
    return rows[0] if rows else None


def _context() -> tuple[OAuthStorage, Any, dict[str, Any]]:
    context, account = require_google_account()
    return OAuthStorage(), context, account


def _summary(row: dict[str, Any]) -> str:
    value = str(
        row.get("snippet")
        or row.get("body_text")
        or "Sin contenido disponible."
    )
    return " ".join(value.split())[:360]


def _favorite_map(
    *,
    client: Any,
    profile_id: str,
    message_ids: list[str],
) -> dict[str, dict[str, Any]]:
    if not message_ids:
        return {}
    rows = _rows(
        client.table("message_watch_rules")
        .select(
            "id,source_message_id,match_type,is_active,notify_in_app,"
            "notify_push,sender_email,normalized_subject"
        )
        .eq("profile_id", profile_id)
        .in_("source_message_id", message_ids)
        .execute()
    )
    return {
        str(row["source_message_id"]): row
        for row in rows
        if row.get("source_message_id")
    }


def list_stored_threads(
    *,
    limit: int = 40,
    offset: int = 0,
    direction: str | None = None,
    triage_category: str | None = None,
    search: str | None = None,
    favorites_only: bool = False,
) -> dict[str, Any]:
    storage, context, account = _context()
    account_id = str(account["id"])
    safe_limit = min(max(limit, 1), 100)
    safe_offset = max(offset, 0)

    if triage_category and triage_category not in TRIAGE_CATEGORIES:
        raise HTTPException(
            status_code=422,
            detail={
                "status": "invalid_category",
                "message": "La categoría solicitada no es válida.",
            },
        )

    response = storage.client.rpc(
        "hms_mail_threads",
        {
            "p_account_id": account_id,
            "p_profile_id": context.user.id,
            "p_search": (search or "").strip() or None,
            "p_triage_category": triage_category,
            "p_direction": direction,
            "p_favorites_only": bool(favorites_only),
            "p_limit": safe_limit,
            "p_offset": safe_offset,
        },
    ).execute()
    rows = _rows(response)
    total = int(rows[0].get("total_count") or 0) if rows else 0

    return {
        "status": "ok",
        "account_id": account_id,
        "limit": safe_limit,
        "offset": safe_offset,
        "total": total,
        "has_more": safe_offset + len(rows) < total,
        "conversations": rows,
    }


def get_stored_conversation(message_id: str) -> dict[str, Any]:
    storage, context, account = _context()
    client = storage.client
    account_id = str(account["id"])

    selected = _first(
        client.table("communication_messages")
        .select("*")
        .eq("account_id", account_id)
        .eq("id", message_id)
        .limit(1)
        .execute()
    )
    if not selected:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "not_found",
                "message": "El correo seleccionado no existe en HMS.",
            },
        )

    query = client.table("communication_messages").select("*").eq(
        "account_id", account_id
    )
    normalized_subject = str(
        selected.get("normalized_subject") or ""
    ).strip()
    correlation_key = str(selected.get("correlation_key") or "").strip()
    thread_id = selected.get("thread_id")

    # Por producto, el tema normalizado agrupa RE, Reply all y reenvíos.
    if normalized_subject:
        query = query.eq("normalized_subject", normalized_subject)
    elif correlation_key:
        query = query.eq("correlation_key", correlation_key)
    elif thread_id:
        query = query.eq("thread_id", str(thread_id))
    else:
        query = query.eq("id", message_id)

    messages = _rows(
        query.order("received_at", desc=False)
        .order("created_at", desc=False)
        .limit(500)
        .execute()
    )
    message_ids = [str(row["id"]) for row in messages]
    favorites = _favorite_map(
        client=client,
        profile_id=context.user.id,
        message_ids=message_ids,
    )

    links = _rows(
        client.table("case_messages")
        .select("message_id,case_id,relation_type,is_primary")
        .in_("message_id", message_ids)
        .execute()
    ) if message_ids else []
    case_ids = sorted(
        {
            str(link["case_id"])
            for link in links
            if link.get("case_id")
        }
    )
    cases = _rows(
        client.table("intelligent_cases")
        .select("id,title,status,priority,risk_score")
        .eq("account_id", account_id)
        .in_("id", case_ids)
        .execute()
    ) if case_ids else []
    case_map = {str(case["id"]): case for case in cases}
    links_by_message: dict[str, list[dict[str, Any]]] = {}
    for link in links:
        links_by_message.setdefault(str(link.get("message_id")), []).append(link)

    enriched: list[dict[str, Any]] = []
    for row in messages:
        row_id = str(row["id"])
        related_cases = [
            case_map[str(link["case_id"])]
            for link in links_by_message.get(row_id, [])
            if str(link.get("case_id")) in case_map
        ]
        enriched.append(
            {
                **row,
                "summary": _summary(row),
                "favorite": favorites.get(row_id),
                "related_cases": related_cases,
            }
        )

    latest = enriched[-1] if enriched else selected
    participants = sorted(
        {
            str(row.get("sender") or "").strip()
            for row in enriched
            if str(row.get("sender") or "").strip()
        }
    )

    return {
        "status": "ok",
        "message_count": len(enriched),
        "latest_message_id": str(latest.get("id") or message_id),
        "subject": latest.get("subject"),
        "normalized_subject": latest.get("normalized_subject"),
        "summary": _summary(latest),
        "participants": participants,
        "messages": enriched,
    }


def get_stored_message(message_id: str) -> dict[str, Any]:
    conversation = get_stored_conversation(message_id)
    for message in conversation["messages"]:
        if str(message.get("id")) == message_id:
            return message
    raise HTTPException(status_code=404, detail="Mensaje no encontrado.")
