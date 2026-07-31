from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.services.event_engine import create_case_event
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
    storage = OAuthStorage()
    active = storage.get_active_credentials(provider="google")

    if not active:
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "message": "No existe una cuenta Google activa.",
            },
        )

    return storage, active["account"]


def list_cases(
    *,
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
    priority: str | None = None,
    search: str | None = None,
) -> dict[str, Any]:
    storage, account = _context()
    safe_limit = min(max(limit, 1), 200)
    safe_offset = max(offset, 0)

    query = (
        storage.client.table("intelligent_cases")
        .select("*")
        .eq("account_id", str(account["id"]))
        .order("risk_score", desc=True)
        .order("last_activity_at", desc=True)
        .range(safe_offset, safe_offset + safe_limit - 1)
    )

    if status:
        query = query.eq("status", status)

    if priority:
        query = query.eq("priority", priority)

    if search and search.strip():
        query = query.ilike(
            "title",
            f"%{search.strip()}%",
        )

    cases = _rows(query.execute())

    return {
        "status": "ok",
        "total": len(cases),
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


def dashboard() -> dict[str, Any]:
    storage, account = _context()
    client = storage.client
    account_id = str(account["id"])
    workspace_id = str(account["workspace_id"])
    today = datetime.now(timezone.utc).date().isoformat()

    cases = _rows(
        (
            client.table("intelligent_cases")
            .select("*")
            .eq("account_id", account_id)
            .order("risk_score", desc=True)
            .order("last_activity_at", desc=True)
            .limit(200)
            .execute()
        )
    )

    now = datetime.now(timezone.utc)

    def is_overdue(case: dict[str, Any]) -> bool:
        value = case.get("due_at")

        if not value:
            return False

        try:
            due = datetime.fromisoformat(
                str(value).replace("Z", "+00:00")
            )

            if due.tzinfo is None:
                due = due.replace(tzinfo=timezone.utc)

            return (
                due < now
                and case.get("status")
                not in ("resolved", "closed", "archived")
            )
        except ValueError:
            return False

    open_cases = [
        case
        for case in cases
        if case.get("status") in _OPEN_STATUSES
    ]

    metrics = {
        "total_open": len(open_cases),
        "critical": sum(
            1
            for case in open_cases
            if case.get("priority") == "critical"
        ),
        "waiting_internal": sum(
            1
            for case in open_cases
            if case.get("waiting_on") == "internal"
        ),
        "waiting_external": sum(
            1
            for case in open_cases
            if case.get("waiting_on") == "external"
        ),
        "overdue": sum(
            1
            for case in open_cases
            if is_overdue(case)
        ),
        "resolved_today": sum(
            1
            for case in cases
            if str(case.get("resolved_at") or "").startswith(today)
        ),
        "unread_notifications": len(
            _rows(
                (
                    client.table("case_notifications")
                    .select("id")
                    .eq("workspace_id", workspace_id)
                    .is_("read_at", "null")
                    .limit(500)
                    .execute()
                )
            )
        ),
    }

    attention = sorted(
        open_cases,
        key=lambda case: (
            int(case.get("risk_score") or 0),
            str(case.get("last_activity_at") or ""),
        ),
        reverse=True,
    )[:20]

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
