from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.services.gmail_sync import (
    _extract_bodies,
    _first_row,
    _format_sender,
    _get_header,
    _get_or_create_thread,
    _parse_addresses,
    _parse_received_at,
    _to_iso,
    _utc_now,
)
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


def _message_direction(labels: list[str]) -> str:
    normalized = {str(label).upper() for label in labels}

    if "DRAFT" in normalized:
        return "draft"
    if "SENT" in normalized and "INBOX" not in normalized:
        return "outbound"
    if "INBOX" in normalized:
        return "inbound"
    return "inbound"


def _references_list(raw_value: str) -> list[str]:
    return [
        item.strip()
        for item in raw_value.split()
        if item.strip()
    ]


def _existing_message_ids(
    *,
    client: Any,
    account_id: str,
    external_ids: list[str],
) -> set[str]:
    if not external_ids:
        return set()

    response = (
        client.table("communication_messages")
        .select("external_message_id")
        .eq("account_id", account_id)
        .in_("external_message_id", external_ids)
        .execute()
    )

    return {
        str(row.get("external_message_id") or "")
        for row in _rows(response)
        if row.get("external_message_id")
    }


def sync_gmail_page(
    *,
    credentials: Credentials,
    batch_size: int = 50,
    page_token: str | None = None,
    query: str | None = None,
    account_id: str | None = None,
) -> dict[str, Any]:
    """
    Sincroniza una página de Gmail.

    El proceso usa lotes pequeños y detección masiva de duplicados.
    El frontend continúa automáticamente mientras exista page token.
    """

    safe_batch_size = min(max(batch_size, 1), 100)
    storage = OAuthStorage()

    if account_id is None:
        _, account = require_google_account()
    else:
        account = storage.get_account(account_id)
        if not account:
            raise HTTPException(
                status_code=404,
                detail={
                    "status": "error",
                    "message": "La cuenta Google de sincronización no existe.",
                },
            )

    account_id = str(account["id"])
    client = storage.client
    started_at = _utc_now()

    inserted = 0
    duplicates = 0
    errors = 0
    error_details: list[dict[str, str]] = []
    inserted_message_ids: list[str] = []

    try:
        gmail_service = build(
            "gmail",
            "v1",
            credentials=credentials,
            cache_discovery=False,
        )

        parameters: dict[str, Any] = {
            "userId": "me",
            "maxResults": safe_batch_size,
        }

        if page_token:
            parameters["pageToken"] = page_token

        if query and query.strip():
            parameters["q"] = query.strip()

        list_response = (
            gmail_service.users()
            .messages()
            .list(**parameters)
            .execute()
        )

        references = [
            item
            for item in (list_response.get("messages") or [])
            if isinstance(item, dict)
            and item.get("id")
        ]

        external_ids = [
            str(item["id"])
            for item in references
        ]

        existing_ids = _existing_message_ids(
            client=client,
            account_id=account_id,
            external_ids=external_ids,
        )

        duplicates = len(existing_ids)

        pending_references = [
            item
            for item in references
            if str(item["id"]) not in existing_ids
        ]

        next_page_token = list_response.get("nextPageToken")

        for reference in pending_references:
            external_message_id = str(reference["id"])

            try:
                raw_message = (
                    gmail_service.users()
                    .messages()
                    .get(
                        userId="me",
                        id=external_message_id,
                        format="full",
                    )
                    .execute()
                )

                payload = raw_message.get("payload") or {}
                headers = payload.get("headers") or []

                external_thread_id = str(
                    raw_message.get("threadId")
                    or external_message_id
                )

                subject = (
                    _get_header(headers, "Subject")
                    or "(Sin asunto)"
                )

                sender_raw = _get_header(headers, "From")
                to_raw = _get_header(headers, "To")
                cc_raw = _get_header(headers, "Cc")
                bcc_raw = _get_header(headers, "Bcc")
                date_header = _get_header(headers, "Date")

                received_at = _parse_received_at(
                    raw_message=raw_message,
                    date_header=date_header,
                )
                received_at_iso = _to_iso(received_at)

                body_text, body_html, has_attachments = (
                    _extract_bodies(payload)
                )

                snippet = str(
                    raw_message.get("snippet") or ""
                ).strip()

                if not body_text:
                    body_text = snippet

                labels = [
                    str(label)
                    for label in (
                        raw_message.get("labelIds") or []
                    )
                    if label
                ]

                recipients = _parse_addresses(to_raw)
                cc = _parse_addresses(cc_raw)
                bcc = _parse_addresses(bcc_raw)
                sender = _format_sender(sender_raw)

                participant_values: list[str] = []

                if sender:
                    participant_values.append(sender)

                for address in recipients + cc + bcc:
                    formatted = (
                        address.get("email")
                        or address.get("name")
                    )

                    if formatted:
                        participant_values.append(formatted)

                participants = ", ".join(
                    dict.fromkeys(participant_values)
                )

                thread = _get_or_create_thread(
                    client=client,
                    account_id=account_id,
                    external_thread_id=external_thread_id,
                    subject=subject,
                    participants=participants,
                    last_message_at=(
                        received_at_iso
                        or _to_iso(_utc_now())
                        or ""
                    ),
                )

                message_payload = {
                    "thread_id": str(thread["id"]),
                    "account_id": account_id,
                    "provider": "google",
                    "external_message_id": external_message_id,
                    "sender": sender,
                    "recipients": recipients,
                    "cc": cc,
                    "bcc": bcc,
                    "subject": subject,
                    "body_text": body_text,
                    "body_html": body_html,
                    "received_at": received_at_iso,
                    "has_attachments": has_attachments,
                    "labels": labels,
                    "is_unread": "UNREAD" in labels,
                    "snippet": snippet,
                    "direction": _message_direction(labels),
                    "internet_message_id": (
                        _get_header(
                            headers,
                            "Message-ID",
                        ).strip()
                        or None
                    ),
                    "in_reply_to": (
                        _get_header(
                            headers,
                            "In-Reply-To",
                        ).strip()
                        or None
                    ),
                    "references_header": _references_list(
                        _get_header(headers, "References")
                    ),
                    "case_processed": False,
                    "ai_processed": False,
                }

                insert_response = (
                    client.table("communication_messages")
                    .insert(message_payload)
                    .execute()
                )

                created_message = _first_row(insert_response)
                if not created_message:
                    raise RuntimeError(
                        "Supabase no confirmó la creación "
                        "del mensaje."
                    )

                inserted += 1
                inserted_message_ids.append(str(created_message["id"]))

            except Exception as error:
                error_text = str(error).lower()

                if (
                    "duplicate key" in error_text
                    or "unique constraint" in error_text
                    or "23505" in error_text
                ):
                    duplicates += 1
                    continue

                errors += 1

                if len(error_details) < 20:
                    error_details.append(
                        {
                            "message_id": external_message_id,
                            "error": str(error),
                        }
                    )

        completed_at = _utc_now()

        if not next_page_token:
            (
                client.table("communication_accounts")
                .update(
                    {
                        "last_sync_at": _to_iso(
                            completed_at
                        )
                    }
                )
                .eq("id", account_id)
                .execute()
            )

        return {
            "status": "ok" if errors == 0 else "partial",
            "connected": True,
            "account_id": account_id,
            "email": account.get("email"),
            "batch_size": safe_batch_size,
            "page_found": len(references),
            "inserted": inserted,
            "inserted_message_ids": inserted_message_ids,
            "duplicates": duplicates,
            "errors": errors,
            "error_details": error_details,
            "next_page_token": next_page_token,
            "has_more": bool(next_page_token),
            "started_at": _to_iso(started_at),
            "completed_at": _to_iso(completed_at),
        }

    except HttpError as error:
        raise HTTPException(
            status_code=502,
            detail={
                "status": "error",
                "message": (
                    "Google Gmail rechazó la sincronización."
                ),
                "technical_detail": str(error),
            },
        ) from error
