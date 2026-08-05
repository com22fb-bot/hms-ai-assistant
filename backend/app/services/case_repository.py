from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException

from app.services.event_engine import create_case_event
from app.security.identity import require_google_account
from app.services.oauth_storage import OAuthStorage


_OPEN_STATUSES = [
    "new",
    "analyzing",
    "in_progress",
    "delegated",
    "waiting_internal",
    "waiting_external",
]


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


def _first_row(response: Any) -> dict[str, Any] | None:
    rows = _rows(response)
    return rows[0] if rows else None


def _context() -> tuple[OAuthStorage, dict[str, Any]]:
    _, account = require_google_account()
    return OAuthStorage(), account


def _response_count(response: Any) -> int:
    value = getattr(response, "count", None)

    if value is None:
        return len(_rows(response))

    try:
        return int(value)
    except (TypeError, ValueError):
        return len(_rows(response))


def _apply_case_filters(
    query: Any,
    *,
    account_id: str,
    status: str | None = None,
    priority: str | None = None,
    search: str | None = None,
) -> Any:
    query = query.eq("account_id", account_id)

    if status:
        query = query.eq("status", status)

    if priority:
        query = query.eq("priority", priority)

    if search and search.strip():
        query = query.ilike(
            "title",
            f"%{search.strip()}%",
        )

    return query


def list_cases(
    *,
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
    priority: str | None = None,
    search: str | None = None,
) -> dict[str, Any]:
    storage, account = _context()
    account_id = str(account["id"])
    safe_limit = min(max(limit, 1), 200)
    safe_offset = max(offset, 0)

    count_query = _apply_case_filters(
        storage.client.table("intelligent_cases").select(
            "id",
            count="exact",
        ),
        account_id=account_id,
        status=status,
        priority=priority,
        search=search,
    )
    total = _response_count(count_query.limit(1).execute())

    data_query = _apply_case_filters(
        storage.client.table("intelligent_cases").select("*"),
        account_id=account_id,
        status=status,
        priority=priority,
        search=search,
    )
    cases = _rows(
        data_query
        .order("risk_score", desc=True)
        .order("last_activity_at", desc=True)
        .range(safe_offset, safe_offset + safe_limit - 1)
        .execute()
    )

    return {
        "status": "ok",
        "total": total,
        "limit": safe_limit,
        "offset": safe_offset,
        "cases": cases,
    }


def get_case(case_id: str) -> dict[str, Any]:
    storage, account = _context()
    client = storage.client

    case = _first_row(
        (
            client.table("intelligent_cases")
            .select("*")
            .eq("account_id", str(account["id"]))
            .eq("id", case_id)
            .limit(1)
            .execute()
        )
    )

    if not case:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "message": "Caso no encontrado.",
            },
        )

    participants = _rows(
        (
            client.table("case_participants")
            .select("*")
            .eq("case_id", case_id)
            .order("message_count", desc=True)
            .execute()
        )
    )

    links = _rows(
        (
            client.table("case_messages")
            .select("message_id,relation_type,is_primary,linked_at")
            .eq("case_id", case_id)
            .order("linked_at")
            .execute()
        )
    )

    messages: list[dict[str, Any]] = []

    for link in links:
        message = _first_row(
            (
                client.table("communication_messages")
                .select(
                    "id,sender,recipients,subject,snippet,body_text,"
                    "received_at,labels,is_unread,direction"
                )
                .eq("id", str(link["message_id"]))
                .limit(1)
                .execute()
            )
        )

        if message:
            messages.append(
                {
                    **message,
                    "relation_type": link.get("relation_type"),
                    "is_primary": link.get("is_primary"),
                    "linked_at": link.get("linked_at"),
                }
            )

    events = _rows(
        (
            client.table("case_events")
            .select("*")
            .eq("case_id", case_id)
            .order("created_at", desc=True)
            .execute()
        )
    )

    return {
        **case,
        "participants": participants,
        "messages": messages,
        "events": events,
    }


def update_case(
    *,
    case_id: str,
    changes: dict[str, Any],
) -> dict[str, Any]:
    storage, account = _context()
    client = storage.client

    current = _first_row(
        (
            client.table("intelligent_cases")
            .select("*")
            .eq("account_id", str(account["id"]))
            .eq("id", case_id)
            .limit(1)
            .execute()
        )
    )

    if not current:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "message": "Caso no encontrado.",
            },
        )

    payload = {
        key: value
        for key, value in changes.items()
        if value is not None
    }

    new_status = payload.get("status")

    if new_status == "resolved":
        payload["resolved_at"] = datetime.now(
            timezone.utc
        ).isoformat()
        payload["waiting_on"] = "none"

    if new_status == "closed":
        payload["closed_at"] = datetime.now(
            timezone.utc
        ).isoformat()
        payload["waiting_on"] = "none"

    updated = _first_row(
        (
            client.table("intelligent_cases")
            .update(payload)
            .eq("id", case_id)
            .execute()
        )
    )

    create_case_event(
        client=client,
        workspace_id=str(account["workspace_id"]),
        case_id=case_id,
        event_type="case_updated",
        level=2 if new_status in ("resolved", "closed") else 1,
        title=(
            "Caso resuelto"
            if new_status == "resolved"
            else "Caso actualizado"
        ),
        description=(
            f"Cambios aplicados: {', '.join(sorted(payload))}"
        ),
        actor_type="user",
        dedupe_key=None,
        metadata={
            "previous_status": current.get("status"),
            "changes": payload,
        },
    )

    return updated or {
        **current,
        **payload,
    }


def _count_cases(
    *,
    client: Any,
    account_id: str,
    statuses: list[str] | None = None,
    priority: str | None = None,
    waiting_on: str | None = None,
    due_before: str | None = None,
    resolved_from: str | None = None,
    resolved_before: str | None = None,
) -> int:
    query = (
        client.table("intelligent_cases")
        .select("id", count="exact")
        .eq("account_id", account_id)
    )

    if statuses:
        query = query.in_("status", statuses)
    if priority:
        query = query.eq("priority", priority)
    if waiting_on:
        query = query.eq("waiting_on", waiting_on)
    if due_before:
        query = query.lt("due_at", due_before)
    if resolved_from:
        query = query.gte("resolved_at", resolved_from)
    if resolved_before:
        query = query.lt("resolved_at", resolved_before)

    return _response_count(query.limit(1).execute())


def dashboard() -> dict[str, Any]:
    storage, account = _context()
    client = storage.client
    account_id = str(account["id"])
    workspace_id = str(account["workspace_id"])
    now = datetime.now(timezone.utc)
    today_start = datetime(
        year=now.year,
        month=now.month,
        day=now.day,
        tzinfo=timezone.utc,
    )
    tomorrow_start = today_start + timedelta(days=1)

    metrics = {
        "total_open": _count_cases(
            client=client,
            account_id=account_id,
            statuses=_OPEN_STATUSES,
        ),
        "critical": _count_cases(
            client=client,
            account_id=account_id,
            statuses=_OPEN_STATUSES,
            priority="critical",
        ),
        "waiting_internal": _count_cases(
            client=client,
            account_id=account_id,
            statuses=_OPEN_STATUSES,
            waiting_on="internal",
        ),
        "waiting_external": _count_cases(
            client=client,
            account_id=account_id,
            statuses=_OPEN_STATUSES,
            waiting_on="external",
        ),
        "overdue": _count_cases(
            client=client,
            account_id=account_id,
            statuses=_OPEN_STATUSES,
            due_before=now.isoformat(),
        ),
        "resolved_today": _count_cases(
            client=client,
            account_id=account_id,
            resolved_from=today_start.isoformat(),
            resolved_before=tomorrow_start.isoformat(),
        ),
        "unread_notifications": _response_count(
            (
                client.table("case_notifications")
                .select("id", count="exact")
                .eq("workspace_id", workspace_id)
                .is_("read_at", "null")
                .limit(1)
                .execute()
            )
        ),
    }

    attention = _rows(
        (
            client.table("intelligent_cases")
            .select("*")
            .eq("account_id", account_id)
            .in_("status", _OPEN_STATUSES)
            .order("risk_score", desc=True)
            .order("last_activity_at", desc=True)
            .limit(20)
            .execute()
        )
    )

    events = _rows(
        (
            client.table("case_events")
            .select("*")
            .eq("workspace_id", workspace_id)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
    )

    return {
        "status": "ok",
        "metrics": metrics,
        "attention": attention,
        "recent_events": events,
    }


def list_notifications(
    *,
    unread_only: bool = True,
    limit: int = 50,
) -> dict[str, Any]:
    storage, account = _context()
    safe_limit = min(max(limit, 1), 200)

    query = (
        storage.client.table("case_notifications")
        .select("*")
        .eq("workspace_id", str(account["workspace_id"]))
        .order("created_at", desc=True)
        .limit(safe_limit)
    )

    if unread_only:
        query = query.is_("read_at", "null")

    notifications = _rows(query.execute())

    return {
        "status": "ok",
        "total": len(notifications),
        "notifications": notifications,
    }
