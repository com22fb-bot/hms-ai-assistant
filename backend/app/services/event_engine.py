from __future__ import annotations

from typing import Any


def _first_row(response: Any) -> dict[str, Any] | None:
    data = getattr(response, "data", None)

    if isinstance(data, list):
        return data[0] if data else None

    if isinstance(data, dict):
        return data

    return None


def create_case_event(
    *,
    client: Any,
    workspace_id: str,
    case_id: str,
    event_type: str,
    level: int,
    title: str,
    description: str | None = None,
    message_id: str | None = None,
    actor_type: str = "system",
    actor_identifier: str | None = None,
    dedupe_key: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    payload = {
        "workspace_id": workspace_id,
        "case_id": case_id,
        "message_id": message_id,
        "event_type": event_type,
        "level": max(0, min(level, 4)),
        "title": title,
        "description": description,
        "actor_type": actor_type,
        "actor_identifier": actor_identifier,
        "dedupe_key": dedupe_key,
        "metadata": metadata or {},
    }

    try:
        response = (
            client.table("case_events")
            .insert(payload)
            .execute()
        )
        event = _first_row(response)
    except Exception as error:
        error_text = str(error).lower()

        if (
            dedupe_key
            and (
                "duplicate key" in error_text
                or "unique constraint" in error_text
                or "23505" in error_text
            )
        ):
            return None

        raise

    if event and level >= 2:
        (
            client.table("case_notifications")
            .insert(
                {
                    "workspace_id": workspace_id,
                    "case_id": case_id,
                    "event_id": event.get("id"),
                    "level": level,
                    "channel": "dashboard",
                    "title": title,
                    "body": description,
                    "metadata": metadata or {},
                }
            )
            .execute()
        )

    return event
