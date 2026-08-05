from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.security.identity import require_google_account
from app.services.oauth_storage import OAuthStorage


def _rows(response: Any) -> list[dict[str, Any]]:
    data = getattr(response, "data", None)

    if isinstance(data, list):
        return [
            item
            for item in data
            if isinstance(item, dict)
        ]

    if isinstance(data, dict):
        return [data]

    return []


def _active_context() -> tuple[OAuthStorage, dict[str, Any]]:
    _, account = require_google_account()
    return OAuthStorage(), account


def list_stored_messages(
    *,
    limit: int = 50,
    offset: int = 0,
    unread_only: bool = False,
    direction: str | None = None,
    search: str | None = None,
    case_processed: bool | None = None,
) -> dict[str, Any]:
    storage, account = _active_context()
    safe_limit = min(max(limit, 1), 200)
    safe_offset = max(offset, 0)

    query = (
        storage.client.table("communication_messages")
        .select(
            "id,thread_id,account_id,provider,external_message_id,"
            "sender,recipients,cc,bcc,subject,body_text,snippet,"
            "received_at,has_attachments,labels,is_unread,"
            "direction,normalized_subject,case_processed,processed_at"
        )
        .eq("account_id", str(account["id"]))
        .order("received_at", desc=True)
        .range(safe_offset, safe_offset + safe_limit - 1)
    )

    if unread_only:
        query = query.eq("is_unread", True)

    if direction:
        query = query.eq("direction", direction)

    if case_processed is not None:
        query = query.eq("case_processed", case_processed)

    if search and search.strip():
        query = query.ilike(
            "subject",
            f"%{search.strip()}%",
        )

    rows = _rows(query.execute())

    return {
        "status": "ok",
        "account_id": str(account["id"]),
        "limit": safe_limit,
        "offset": safe_offset,
        "total": len(rows),
        "has_more": len(rows) == safe_limit,
        "messages": rows,
    }


def get_stored_message(message_id: str) -> dict[str, Any]:
    storage, account = _active_context()

    response = (
        storage.client.table("communication_messages")
        .select("*")
        .eq("account_id", str(account["id"]))
        .eq("id", message_id)
        .limit(1)
        .execute()
    )

    rows = _rows(response)

    if not rows:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "message": "Mensaje almacenado no encontrado.",
            },
        )

    return rows[0]
