"""
Sincronización de Gmail hacia Supabase.

HMS AI Assistant
Sprint 3.1

Responsabilidades:

- Obtener la cuenta Google activa.
- Consultar mensajes de Gmail.
- Descargar el contenido completo de cada mensaje.
- Crear o actualizar hilos.
- Guardar mensajes sin duplicarlos.
- Preparar mensajes para análisis con IA.
- Actualizar la fecha de última sincronización.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from email.utils import getaddresses, parsedate_to_datetime
from typing import Any

from fastapi import HTTPException
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.services.oauth_storage import OAuthStorage


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc).isoformat()


def _parse_iso_datetime(value: Any) -> datetime | None:
    if not value:
        return None

    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        parsed = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    else:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def _first_row(response: Any) -> dict[str, Any] | None:
    data = getattr(response, "data", None)

    if not data:
        return None

    if isinstance(data, list):
        return data[0] if data else None

    if isinstance(data, dict):
        return data

    return None


def _get_header(
    headers: list[dict[str, Any]],
    name: str,
) -> str:
    expected = name.lower()

    for header in headers:
        if str(header.get("name", "")).lower() == expected:
            return str(header.get("value", ""))

    return ""


def _decode_base64url(data: str | None) -> str:
    if not data:
        return ""

    try:
        padding = "=" * (-len(data) % 4)
        decoded = base64.urlsafe_b64decode(
            (data + padding).encode("utf-8")
        )

        return decoded.decode(
            "utf-8",
            errors="replace",
        )

    except Exception:
        return ""


def _extract_bodies(
    payload: dict[str, Any],
) -> tuple[str, str, bool]:
    """
    Extrae texto plano, HTML e indicador de archivos adjuntos.

    Recorre estructuras MIME anidadas.
    """

    plain_parts: list[str] = []
    html_parts: list[str] = []
    has_attachments = False

    def walk(part: dict[str, Any]) -> None:
        nonlocal has_attachments

        mime_type = str(
            part.get("mimeType", "")
        ).lower()

        filename = str(
            part.get("filename", "")
        ).strip()

        body = part.get("body") or {}
        body_data = body.get("data")
        attachment_id = body.get("attachmentId")

        if filename or attachment_id:
            has_attachments = True

        if body_data:
            decoded = _decode_base64url(body_data)

            if mime_type == "text/plain":
                plain_parts.append(decoded)

            elif mime_type == "text/html":
                html_parts.append(decoded)

        for child in part.get("parts") or []:
            if isinstance(child, dict):
                walk(child)

    walk(payload)

    return (
        "\n\n".join(
            part.strip()
            for part in plain_parts
            if part.strip()
        ),
        "\n\n".join(
            part.strip()
            for part in html_parts
            if part.strip()
        ),
        has_attachments,
    )


def _parse_addresses(raw_value: str) -> list[dict[str, str]]:
    if not raw_value:
        return []

    parsed: list[dict[str, str]] = []

    for name, email in getaddresses([raw_value]):
        cleaned_email = email.strip()
        cleaned_name = name.strip()

        if not cleaned_email and not cleaned_name:
            continue

        parsed.append(
            {
                "name": cleaned_name,
                "email": cleaned_email,
            }
        )

    return parsed


def _format_sender(raw_value: str) -> str:
    addresses = _parse_addresses(raw_value)

    if not addresses:
        return raw_value.strip()

    sender = addresses[0]
    name = sender.get("name", "")
    email = sender.get("email", "")

    if name and email:
        return f"{name} <{email}>"

    return email or name or raw_value.strip()


def _parse_received_at(
    raw_message: dict[str, Any],
    date_header: str,
) -> datetime:
    internal_date = raw_message.get("internalDate")

    if internal_date:
        try:
            milliseconds = int(internal_date)

            return datetime.fromtimestamp(
                milliseconds / 1000,
                tz=timezone.utc,
            )
        except (TypeError, ValueError, OSError):
            pass

    if date_header:
        try:
            parsed = parsedate_to_datetime(date_header)

            if parsed.tzinfo is None:
                parsed = parsed.replace(
                    tzinfo=timezone.utc
                )

            return parsed.astimezone(timezone.utc)

        except (TypeError, ValueError, OverflowError):
            pass

    return _utc_now()


def _build_incremental_query(
    last_sync_at: str | None,
    custom_query: str | None,
) -> str | None:
    if custom_query and custom_query.strip():
        return custom_query.strip()

    parsed_last_sync = _parse_iso_datetime(last_sync_at)

    if parsed_last_sync is None:
        return None

    # Gmail acepta timestamps Unix en la búsqueda "after:".
    timestamp = int(parsed_last_sync.timestamp())

    return f"after:{timestamp}"


def _get_message_references(
    gmail_service: Any,
    limit: int,
    query: str | None,
) -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []
    page_token: str | None = None

    while len(references) < limit:
        page_size = min(
            100,
            limit - len(references),
        )

        parameters: dict[str, Any] = {
            "userId": "me",
            "maxResults": page_size,
        }

        if query:
            parameters["q"] = query

        if page_token:
            parameters["pageToken"] = page_token

        response = (
            gmail_service.users()
            .messages()
            .list(**parameters)
            .execute()
        )

        batch = response.get("messages") or []

        references.extend(
            item
            for item in batch
            if isinstance(item, dict)
        )

        page_token = response.get("nextPageToken")

        if not page_token or not batch:
            break

    return references[:limit]


def _find_existing_message(
    client: Any,
    account_id: str,
    external_message_id: str,
) -> dict[str, Any] | None:
    response = (
        client.table("communication_messages")
        .select("id,external_message_id")
        .eq("account_id", account_id)
        .eq(
            "external_message_id",
            external_message_id,
        )
        .limit(1)
        .execute()
    )

    return _first_row(response)


def _get_or_create_thread(
    client: Any,
    account_id: str,
    external_thread_id: str,
    subject: str,
    participants: str,
    last_message_at: str,
) -> dict[str, Any]:
    response = (
        client.table("communication_threads")
        .select("*")
        .eq("account_id", account_id)
        .eq(
            "external_thread_id",
            external_thread_id,
        )
        .limit(1)
        .execute()
    )

    existing = _first_row(response)

    payload = {
        "account_id": account_id,
        "provider": "google",
        "external_thread_id": external_thread_id,
        "subject": subject,
        "participants": participants,
        "last_message_at": last_message_at,
    }

    if existing:
        current_last_message = _parse_iso_datetime(
            existing.get("last_message_at")
        )

        incoming_last_message = _parse_iso_datetime(
            last_message_at
        )

        should_update = (
            current_last_message is None
            or incoming_last_message is None
            or incoming_last_message >= current_last_message
        )

        if should_update:
            update_response = (
                client.table("communication_threads")
                .update(
                    {
                        "subject": subject,
                        "participants": participants,
                        "last_message_at": last_message_at,
                    }
                )
                .eq("id", existing["id"])
                .execute()
            )

            updated = _first_row(update_response)

            if updated:
                return updated

        return existing

    create_response = (
        client.table("communication_threads")
        .insert(payload)
        .execute()
    )

    created = _first_row(create_response)

    if not created:
        # Protección ante una creación concurrente.
        retry_response = (
            client.table("communication_threads")
            .select("*")
            .eq("account_id", account_id)
            .eq(
                "external_thread_id",
                external_thread_id,
            )
            .limit(1)
            .execute()
        )

        created = _first_row(retry_response)

    if not created:
        raise RuntimeError(
            "Supabase no confirmó la creación del hilo."
        )

    return created


def sync_gmail_messages(
    credentials: Credentials,
    limit: int = 100,
    query: str | None = None,
) -> dict[str, Any]:
    """
    Sincroniza mensajes desde Gmail hacia Supabase.

    Los mensajes existentes se omiten usando la restricción:

        unique(account_id, external_message_id)
    """

    safe_limit = min(
        max(limit, 1),
        500,
    )

    storage = OAuthStorage()

    active_connection = storage.get_active_credentials(
        provider="google"
    )

    if not active_connection:
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "connected": False,
                "message": (
                    "No existe una cuenta Google activa."
                ),
                "login_url": "/auth/google/login",
            },
        )

    account = active_connection["account"]
    account_id = str(account["id"])
    client = storage.client

    effective_query = _build_incremental_query(
        last_sync_at=account.get("last_sync_at"),
        custom_query=query,
    )

    started_at = _utc_now()

    inserted = 0
    duplicates = 0
    errors = 0
    error_details: list[dict[str, str]] = []

    try:
        gmail_service = build(
            "gmail",
            "v1",
            credentials=credentials,
            cache_discovery=False,
        )

        references = _get_message_references(
            gmail_service=gmail_service,
            limit=safe_limit,
            query=effective_query,
        )

        for reference in references:
            external_message_id = str(
                reference.get("id", "")
            ).strip()

            if not external_message_id:
                errors += 1
                error_details.append(
                    {
                        "message_id": "",
                        "error": (
                            "Gmail devolvió una referencia "
                            "sin identificador."
                        ),
                    }
                )
                continue

            try:
                existing = _find_existing_message(
                    client=client,
                    account_id=account_id,
                    external_message_id=external_message_id,
                )

                if existing:
                    duplicates += 1
                    continue

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

                sender_raw = _get_header(
                    headers,
                    "From",
                )

                to_raw = _get_header(
                    headers,
                    "To",
                )

                cc_raw = _get_header(
                    headers,
                    "Cc",
                )

                bcc_raw = _get_header(
                    headers,
                    "Bcc",
                )

                date_header = _get_header(
                    headers,
                    "Date",
                )

                received_at = _parse_received_at(
                    raw_message=raw_message,
                    date_header=date_header,
                )

                received_at_iso = _to_iso(
                    received_at
                )

                body_text, body_html, has_attachments = (
                    _extract_bodies(payload)
                )

                snippet = str(
                    raw_message.get("snippet") or ""
                ).strip()

                labels = [
                    str(label)
                    for label in (
                        raw_message.get("labelIds") or []
                    )
                    if label
                ]

                is_unread = "UNREAD" in labels

                if not body_text:
                    body_text = snippet

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
                    last_message_at=received_at_iso
                    or _to_iso(_utc_now())
                    or "",
                )

                message_payload = {
                    "thread_id": str(thread["id"]),
                    "account_id": account_id,
                    "provider": "google",
                    "external_message_id": (
                        external_message_id
                    ),
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
                    "is_unread": is_unread,
                    "snippet": snippet,
                    "ai_processed": False,
                }

                insert_response = (
                    client.table("communication_messages")
                    .insert(message_payload)
                    .execute()
                )

                created_message = _first_row(
                    insert_response
                )

                if not created_message:
                    raise RuntimeError(
                        "Supabase no confirmó la creación "
                        "del mensaje."
                    )

                inserted += 1

            except Exception as error:
                # Una colisión por sincronizaciones concurrentes
                # se contabiliza como duplicado.
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
            "status": (
                "ok"
                if errors == 0
                else "partial"
            ),
            "connected": True,
            "account_id": account_id,
            "email": account.get("email"),
            "requested_limit": safe_limit,
            "gmail_query": effective_query,
            "found": len(references),
            "inserted": inserted,
            "duplicates": duplicates,
            "errors": errors,
            "error_details": error_details,
            "started_at": _to_iso(started_at),
            "last_sync_at": _to_iso(completed_at),
        }

    except HttpError as error:
        raise HTTPException(
            status_code=502,
            detail={
                "status": "error",
                "connected": True,
                "message": (
                    "Google Gmail rechazó la sincronización."
                ),
                "technical_detail": str(error),
            },
        ) from error

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "connected": True,
                "message": (
                    "No fue posible sincronizar Gmail "
                    "con Supabase."
                ),
                "technical_detail": str(error),
            },
        ) from error
