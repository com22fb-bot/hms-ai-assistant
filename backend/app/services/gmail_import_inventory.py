from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.database.supabase import get_supabase_client


LOCAL_TIMEZONE = ZoneInfo("America/Chihuahua")
INITIAL_HISTORY_DAYS = 183
EXCLUDED_QUERY = "-in:spam -in:trash -in:drafts"


def _service(credentials: Credentials) -> Any:
    return build(
        "gmail",
        "v1",
        credentials=credentials,
        cache_discovery=False,
    )


def _rows(response: Any) -> list[dict[str, Any]]:
    data = getattr(response, "data", None)

    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]

    if isinstance(data, dict):
        return [data]

    return []


def _list_message_ids(
    service: Any,
    *,
    query: str,
    include_spam_trash: bool = False,
) -> list[str]:
    message_ids: list[str] = []
    page_token: str | None = None

    while True:
        response = (
            service.users()
            .messages()
            .list(
                userId="me",
                q=query,
                maxResults=500,
                pageToken=page_token,
                includeSpamTrash=include_spam_trash,
            )
            .execute(num_retries=2)
        )

        for item in response.get("messages") or []:
            message_id = str(item.get("id") or "").strip()
            if message_id:
                message_ids.append(message_id)

        page_token = (
            str(response.get("nextPageToken") or "").strip() or None
        )
        if page_token is None:
            break

    return message_ids


def _count_query(
    service: Any,
    query: str,
    *,
    include_spam_trash: bool = False,
) -> int:
    return len(
        set(
            _list_message_ids(
                service,
                query=query,
                include_spam_trash=include_spam_trash,
            )
        )
    )


def initial_import_snapshot(
    credentials: Credentials,
    *,
    cutoff_at: datetime | None = None,
) -> dict[str, Any]:
    current = cutoff_at or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)

    current = current.astimezone(timezone.utc)
    start = current - timedelta(days=INITIAL_HISTORY_DAYS)

    query = (
        f"after:{int(start.timestamp())} "
        f"before:{int(current.timestamp())} "
        f"{EXCLUDED_QUERY}"
    ).strip()

    service = _service(credentials)
    ids = _list_message_ids(
        service,
        query=query,
        include_spam_trash=False,
    )
    unique_ids = sorted(set(ids))

    return {
        "query": query,
        "eligible_messages": len(unique_ids),
        "snapshot_at_utc": current.isoformat(),
        "period_start_utc": start.isoformat(),
        "period_end_utc": current.isoformat(),
        "period_start_local": start.astimezone(
            LOCAL_TIMEZONE
        ).isoformat(),
        "period_end_local": current.astimezone(
            LOCAL_TIMEZONE
        ).isoformat(),
        "timezone": "America/Chihuahua",
        "history_days": INITIAL_HISTORY_DAYS,
    }


def inventory(credentials: Credentials) -> dict[str, Any]:
    service = _service(credentials)
    profile = (
        service.users()
        .getProfile(userId="me")
        .execute(num_retries=2)
    )
    snapshot = initial_import_snapshot(credentials)

    base_query = snapshot["query"]
    breakdown_queries = {
        "received": f"({base_query}) in:inbox",
        "sent": f"({base_query}) in:sent",
        "unread": f"({base_query}) is:unread",
        "important": f"({base_query}) is:important",
        "updates": f"({base_query}) category:updates",
        "promotions": f"({base_query}) category:promotions",
        "social": f"({base_query}) category:social",
        "forums": f"({base_query}) category:forums",
    }

    breakdown = [
        {
            "key": key,
            "count": _count_query(service, query),
        }
        for key, query in breakdown_queries.items()
    ]

    excluded = {
        "drafts": _count_query(
            service,
            "in:drafts newer_than:6m",
        ),
        "spam": _count_query(
            service,
            "in:spam newer_than:6m",
            include_spam_trash=True,
        ),
        "trash": _count_query(
            service,
            "in:trash newer_than:6m",
            include_spam_trash=True,
        ),
    }

    return {
        "status": "ok",
        "mode": "initial_six_month_inventory",
        "email": profile.get("emailAddress"),
        "provider": "google",
        "provider_label": "Google",
        "profile_messages_total": int(
            profile.get("messagesTotal") or 0
        ),
        "profile_threads_total": int(
            profile.get("threadsTotal") or 0
        ),
        **snapshot,
        "breakdown": breakdown,
        "excluded": excluded,
        "notice": (
            "HMS importará los mensajes elegibles de los últimos seis "
            "meses. Spam, Papelera y Borradores quedan excluidos. "
            "El buzón original no se modifica."
        ),
    }


def _list_stored_message_ids(account_id: str) -> list[str]:
    client = get_supabase_client()
    message_ids: list[str] = []
    page_size = 1000
    offset = 0

    while True:
        response = (
            client.table("communication_messages")
            .select("external_message_id")
            .eq("account_id", account_id)
            .order("id", desc=False)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = _rows(response)

        for row in rows:
            message_id = str(
                row.get("external_message_id") or ""
            ).strip()
            if message_id:
                message_ids.append(message_id)

        if len(rows) < page_size:
            break

        offset += page_size

    return message_ids


def compare_inventory(
    credentials: Credentials,
    account_id: str,
) -> dict[str, Any]:
    service = _service(credentials)
    profile = (
        service.users()
        .getProfile(userId="me")
        .execute(num_retries=2)
    )
    snapshot = initial_import_snapshot(credentials)
    gmail_ids = _list_message_ids(
        service,
        query=snapshot["query"],
        include_spam_trash=False,
    )
    stored_ids = _list_stored_message_ids(account_id)

    gmail_counter = Counter(gmail_ids)
    stored_counter = Counter(stored_ids)
    gmail_unique = set(gmail_counter)
    stored_unique = set(stored_counter)

    return {
        "status": "ok",
        "mode": "read_only_six_month_comparison",
        "snapshot_at_utc": snapshot["snapshot_at_utc"],
        "snapshot_at_local": datetime.fromisoformat(
            snapshot["snapshot_at_utc"]
        ).astimezone(LOCAL_TIMEZONE).isoformat(),
        "timezone": "America/Chihuahua",
        "email": profile.get("emailAddress"),
        "gmail": {
            "eligible_unique_ids": len(gmail_unique),
            "duplicate_ids": sorted(
                message_id
                for message_id, count in gmail_counter.items()
                if count > 1
            ),
        },
        "hms": {
            "stored_unique_ids": len(stored_unique),
            "duplicate_ids": sorted(
                message_id
                for message_id, count in stored_counter.items()
                if count > 1
            ),
        },
        "comparison": {
            "present_in_both": len(gmail_unique & stored_unique),
            "missing_in_hms": len(gmail_unique - stored_unique),
            "only_in_hms": len(stored_unique - gmail_unique),
        },
        "notice": (
            "Comparación de solo lectura limitada al historial inicial "
            "de seis meses. No modifica Gmail ni HMS."
        ),
    }
