from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.database.supabase import get_supabase_client


CATEGORY_QUERIES: dict[str, str] = {
    "all": "in:anywhere",
    "inbox": "in:inbox",
    "sent": "in:sent",
    "important": "is:important",
    "starred": "is:starred",
    "unread": "is:unread",
    "personal": "category:personal",
    "updates": "category:updates",
    "promotions": "category:promotions",
    "social": "category:social",
    "forums": "category:forums",
    "drafts": "in:drafts",
    "spam": "in:spam",
    "trash": "in:trash",
}

CATEGORY_LABELS: dict[str, str] = {
    "all": "Todos los correos",
    "inbox": "Recibidos",
    "sent": "Enviados",
    "important": "Importantes",
    "starred": "Destacados",
    "unread": "No leídos",
    "personal": "Personal",
    "updates": "Actualizaciones",
    "promotions": "Promociones",
    "social": "Social",
    "forums": "Foros",
    "drafts": "Borradores",
    "spam": "Spam",
    "trash": "Papelera",
}

CATEGORY_SYSTEM_LABELS: dict[str, str] = {
    "inbox": "INBOX",
    "sent": "SENT",
    "important": "IMPORTANT",
    "starred": "STARRED",
    "unread": "UNREAD",
    "personal": "CATEGORY_PERSONAL",
    "updates": "CATEGORY_UPDATES",
    "promotions": "CATEGORY_PROMOTIONS",
    "social": "CATEGORY_SOCIAL",
    "forums": "CATEGORY_FORUMS",
    "drafts": "DRAFT",
    "spam": "SPAM",
    "trash": "TRASH",
}

SENSITIVE_CATEGORIES = {"spam", "trash", "drafts"}


@dataclass(frozen=True)
class ImportSelection:
    keys: list[str]
    query: str


def _service(credentials: Credentials) -> Any:
    return build(
        "gmail",
        "v1",
        credentials=credentials,
        cache_discovery=False,
    )


def _query_estimate(service: Any, query: str) -> int:
    response = (
        service.users()
        .messages()
        .list(
            userId="me",
            q=query,
            maxResults=1,
            includeSpamTrash=True,
        )
        .execute(num_retries=2)
    )
    return int(response.get("resultSizeEstimate") or 0)


def _label_count(service: Any, label_id: str) -> int | None:
    try:
        response = (
            service.users()
            .labels()
            .get(userId="me", id=label_id)
            .execute(num_retries=2)
        )
    except HttpError as exc:
        status = getattr(exc.resp, "status", None)
        if status in {400, 404}:
            return None
        raise

    value = response.get("messagesTotal")
    return int(value) if value is not None else None


def build_selection(keys: list[str]) -> ImportSelection:
    normalized: list[str] = []

    for key in keys:
        clean = str(key).strip().lower()
        if clean in CATEGORY_QUERIES and clean not in normalized:
            normalized.append(clean)

    if not normalized:
        raise ValueError("Selecciona al menos una categoría.")

    if "all" in normalized:
        return ImportSelection(
            keys=["all"],
            query=CATEGORY_QUERIES["all"],
        )

    query = " OR ".join(
        f"({CATEGORY_QUERIES[key]})" for key in normalized
    )
    return ImportSelection(keys=normalized, query=query)


def inventory(credentials: Credentials) -> dict[str, Any]:
    service = _service(credentials)
    profile = (
        service.users()
        .getProfile(userId="me")
        .execute(num_retries=2)
    )

    total_messages = int(profile.get("messagesTotal") or 0)
    categories: list[dict[str, Any]] = []

    for key, query in CATEGORY_QUERIES.items():
        count: int
        count_source: str

        if key == "all":
            count = total_messages
            count_source = "profile"
        else:
            label_id = CATEGORY_SYSTEM_LABELS.get(key)
            label_count = (
                _label_count(service, label_id)
                if label_id
                else None
            )

            if label_count is None:
                count = _query_estimate(service, query)
                count_source = "query_estimate"
            else:
                count = label_count
                count_source = "label"

        categories.append(
            {
                "key": key,
                "label": CATEGORY_LABELS[key],
                "query": query,
                "count": count,
                "count_source": count_source,
                "sensitive": key in SENSITIVE_CATEGORIES,
            }
        )

    return {
        "status": "ok",
        "mode": "inventory_only",
        "email": profile.get("emailAddress"),
        "history_id": profile.get("historyId"),
        "messages_total": total_messages,
        "threads_total": int(profile.get("threadsTotal") or 0),
        "categories": categories,
        "notice": (
            "Este inventario no importa, elimina, archiva ni modifica "
            "mensajes de Gmail."
        ),
    }


def preview(
    credentials: Credentials,
    keys: list[str],
) -> dict[str, Any]:
    selection = build_selection(keys)
    service = _service(credentials)

    return {
        "status": "ok",
        "mode": "inventory_only",
        "selected": selection.keys,
        "query": selection.query,
        "unique_estimate": _query_estimate(
            service,
            selection.query,
        ),
        "notice": (
            "La cifra única es la estimación reportada por Gmail. "
            "La importación continúa bloqueada hasta revisar el inventario."
        ),
    }


def _rows(response: Any) -> list[dict[str, Any]]:
    data = getattr(response, "data", None)

    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]

    if isinstance(data, dict):
        return [data]

    return []


def _list_all_gmail_message_ids(service: Any) -> list[str]:
    message_ids: list[str] = []
    page_token: str | None = None

    while True:
        response = (
            service.users()
            .messages()
            .list(
                userId="me",
                q="in:anywhere",
                maxResults=500,
                pageToken=page_token,
                includeSpamTrash=True,
            )
            .execute(num_retries=2)
        )

        for item in response.get("messages") or []:
            message_id = str(item.get("id") or "").strip()
            if message_id:
                message_ids.append(message_id)

        page_token = str(response.get("nextPageToken") or "").strip() or None
        if page_token is None:
            break

    return message_ids


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
            message_id = str(row.get("external_message_id") or "").strip()
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
    """Compare Gmail message IDs with HMS storage without changing either side."""

    service = _service(credentials)
    profile = (
        service.users()
        .getProfile(userId="me")
        .execute(num_retries=2)
    )

    gmail_ids = _list_all_gmail_message_ids(service)
    stored_ids = _list_stored_message_ids(account_id)

    gmail_counter = Counter(gmail_ids)
    stored_counter = Counter(stored_ids)

    gmail_unique = set(gmail_counter)
    stored_unique = set(stored_counter)

    common = sorted(gmail_unique & stored_unique)
    missing_in_hms = sorted(gmail_unique - stored_unique)
    only_in_hms = sorted(stored_unique - gmail_unique)
    duplicate_gmail_ids = sorted(
        message_id
        for message_id, count in gmail_counter.items()
        if count > 1
    )
    duplicate_stored_ids = sorted(
        message_id
        for message_id, count in stored_counter.items()
        if count > 1
    )

    profile_total = int(profile.get("messagesTotal") or 0)

    return {
        "status": "ok",
        "mode": "read_only_comparison",
        "snapshot_at": datetime.now(timezone.utc).isoformat(),
        "email": profile.get("emailAddress"),
        "history_id": profile.get("historyId"),
        "account_id": account_id,
        "gmail": {
            "profile_total": profile_total,
            "listed_rows": len(gmail_ids),
            "unique_ids": len(gmail_unique),
            "profile_matches_list": profile_total == len(gmail_unique),
            "duplicate_ids": duplicate_gmail_ids,
        },
        "hms": {
            "stored_rows": len(stored_ids),
            "unique_ids": len(stored_unique),
            "duplicate_ids": duplicate_stored_ids,
        },
        "comparison": {
            "present_in_both": len(common),
            "missing_in_hms": len(missing_in_hms),
            "only_in_hms": len(only_in_hms),
        },
        "ids": {
            "missing_in_hms": missing_in_hms,
            "only_in_hms": only_in_hms,
            "duplicate_in_gmail": duplicate_gmail_ids,
            "duplicate_in_hms": duplicate_stored_ids,
        },
        "notice": (
            "Comparación de solo lectura. No importa, elimina, archiva, "
            "etiqueta ni modifica mensajes en Gmail o HMS."
        ),
    }
