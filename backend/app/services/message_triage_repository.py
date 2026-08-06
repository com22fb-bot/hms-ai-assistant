from __future__ import annotations

from typing import Any

from app.security.identity import require_google_account
from app.services.oauth_storage import OAuthStorage


TRIAGE_CATEGORIES: tuple[str, ...] = (
    "action_required",
    "waiting_external",
    "review",
    "notice",
    "social",
    "promotional",
    "automated",
    "informational",
    "unreviewed",
)


def _rows(response: Any) -> list[dict[str, Any]]:
    data = getattr(response, "data", None)
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def _count(response: Any) -> int:
    value = getattr(response, "count", None)
    if value is None:
        return len(_rows(response))
    try:
        return int(value)
    except (TypeError, ValueError):
        return len(_rows(response))


def triage_summary(
    *,
    limit_per_category: int = 8,
) -> dict[str, Any]:
    _, account = require_google_account()
    client = OAuthStorage().client
    account_id = str(account["id"])
    safe_limit = min(max(limit_per_category, 1), 20)
    categories: list[dict[str, Any]] = []

    for category in TRIAGE_CATEGORIES:
        count_response = (
            client.table("communication_messages")
            .select("id", count="exact")
            .eq("account_id", account_id)
            .eq("triage_category", category)
            .limit(1)
            .execute()
        )
        data_response = (
            client.table("communication_messages")
            .select(
                "id,sender,subject,snippet,received_at,is_unread,"
                "triage_category,actionability_score,triage_reason"
            )
            .eq("account_id", account_id)
            .eq("triage_category", category)
            .order("received_at", desc=True)
            .limit(safe_limit)
            .execute()
        )
        categories.append(
            {
                "key": category,
                "count": _count(count_response),
                "messages": _rows(data_response),
            }
        )

    total_response = (
        client.table("communication_messages")
        .select("id", count="exact")
        .eq("account_id", account_id)
        .limit(1)
        .execute()
    )

    return {
        "status": "ok",
        "account_id": account_id,
        "total": _count(total_response),
        "categories": categories,
    }
