from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _first_row(response: Any) -> dict[str, Any] | None:
    data = getattr(response, "data", None)

    if isinstance(data, list):
        return data[0] if data else None

    if isinstance(data, dict):
        return data

    return None


def register_pattern(
    *,
    client: Any,
    workspace_id: str,
    pattern_type: str,
    pattern_key: str,
    pattern_value: dict[str, Any],
) -> None:
    normalized_key = pattern_key.strip().lower()

    if not normalized_key:
        return

    response = (
        client.table("organizational_patterns")
        .select("*")
        .eq("workspace_id", workspace_id)
        .eq("pattern_type", pattern_type)
        .eq("pattern_key", normalized_key)
        .limit(1)
        .execute()
    )

    existing = _first_row(response)
    now = _utc_iso()

    if not existing:
        (
            client.table("organizational_patterns")
            .insert(
                {
                    "workspace_id": workspace_id,
                    "pattern_type": pattern_type,
                    "pattern_key": normalized_key,
                    "pattern_value": pattern_value,
                    "occurrences": 1,
                    "confidence": 0.5000,
                    "first_seen_at": now,
                    "last_seen_at": now,
                }
            )
            .execute()
        )
        return

    occurrences = int(existing.get("occurrences") or 0) + 1
    confidence = min(0.95, 0.50 + min(occurrences, 45) * 0.01)

    (
        client.table("organizational_patterns")
        .update(
            {
                "pattern_value": pattern_value,
                "occurrences": occurrences,
                "confidence": confidence,
                "last_seen_at": now,
            }
        )
        .eq("id", existing["id"])
        .execute()
    )
