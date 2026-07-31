from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from app.services.message_repository import (
    get_stored_message,
    list_stored_messages,
)


router = APIRouter(
    prefix="/messages",
    tags=["Stored Messages"],
)


@router.get("/stored")
def stored_messages(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    unread_only: bool = Query(default=False),
    direction: str | None = Query(default=None),
    search: str | None = Query(default=None),
    case_processed: bool | None = Query(default=None),
) -> dict[str, Any]:
    return list_stored_messages(
        limit=limit,
        offset=offset,
        unread_only=unread_only,
        direction=direction,
        search=search,
        case_processed=case_processed,
    )


@router.get("/stored/{message_id}")
def stored_message(message_id: str) -> dict[str, Any]:
    return get_stored_message(message_id)
