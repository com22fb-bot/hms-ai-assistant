from __future__ import annotations

from email.utils import parseaddr
from typing import Any

from fastapi import HTTPException
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from models import GmailMessage


def create_credentials(
    stored_credentials: dict[str, Any],
    client_id: str,
    client_secret: str,
) -> Credentials:
    if not stored_credentials:
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "connected": False,
                "message": "No hay una cuenta de Google conectada.",
                "login_url": "/auth/google/login",
            },
        )

    credentials = Credentials(
        token=stored_credentials.get("token"),
        refresh_token=stored_credentials.get("refresh_token"),
        token_uri=stored_credentials.get(
            "token_uri",
            "https://oauth2.googleapis.com/token",
        ),
        client_id=client_id,
        client_secret=client_secret,
        scopes=stored_credentials.get("scopes", []),
    )

    try:
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(GoogleRequest())
            stored_credentials["token"] = credentials.token

            if credentials.expiry:
                stored_credentials["expiry"] = (
                    credentials.expiry.isoformat()
                )

        if not credentials.valid:
            raise HTTPException(
                status_code=401,
                detail={
                    "status": "error",
                    "connected": False,
                    "message": (
                        "La sesión de Google expiró. "
                        "Vuelve a conectar la cuenta."
                    ),
                    "login_url": "/auth/google/login",
                },
            )

        return credentials

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "connected": False,
                "message": "No fue posible renovar la sesión de Google.",
                "technical_detail": str(error),
                "login_url": "/auth/google/login",
            },
        ) from error


def get_header(
    headers: list[dict[str, str]],
    header_name: str,
) -> str:
    expected_name = header_name.lower()

    for header in headers:
        if header.get("name", "").lower() == expected_name:
            return header.get("value", "")

    return ""


def normalize_message(
    raw_message: dict[str, Any],
) -> GmailMessage:
    payload = raw_message.get("payload", {})
    headers = payload.get("headers", [])
    labels = raw_message.get("labelIds", [])

    sender_raw = get_header(headers, "From")
    sender_name, sender_email = parseaddr(sender_raw)

    if not sender_name:
        sender_name = (
            sender_email
            or sender_raw
            or "Remitente desconocido"
        )

    return GmailMessage(
        id=raw_message.get("id", ""),
        thread_id=raw_message.get("threadId", ""),
        subject=get_header(headers, "Subject") or "(Sin asunto)",
        sender=sender_name,
        sender_email=sender_email or None,
        recipient=get_header(headers, "To") or None,
        received_at=get_header(headers, "Date") or None,
        snippet=raw_message.get("snippet", ""),
        is_unread="UNREAD" in labels,
        labels=labels,
    )


def list_messages(
    credentials: Credentials,
    max_results: int = 20,
    query: str | None = None,
) -> list[GmailMessage]:
    safe_max_results = min(max(max_results, 1), 100)

    try:
        gmail_service = build(
            "gmail",
            "v1",
            credentials=credentials,
            cache_discovery=False,
        )

        request_parameters: dict[str, Any] = {
            "userId": "me",
            "maxResults": safe_max_results,
        }

        if query:
            request_parameters["q"] = query

        response = (
            gmail_service.users()
            .messages()
            .list(**request_parameters)
            .execute()
        )

        references = response.get("messages", [])
        messages: list[GmailMessage] = []

        for reference in references:
            raw_message = (
                gmail_service.users()
                .messages()
                .get(
                    userId="me",
                    id=reference["id"],
                    format="metadata",
                    metadataHeaders=[
                        "From",
                        "To",
                        "Subject",
                        "Date",
                    ],
                )
                .execute()
            )

            messages.append(normalize_message(raw_message))

        return messages

    except HttpError as error:
        google_status = getattr(error.resp, "status", 502)

        raise HTTPException(
            status_code=google_status,
            detail={
                "status": "error",
                "message": "No fue posible leer Gmail.",
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
                "message": "Ocurrió un error al procesar los correos.",
                "technical_detail": str(error),
            },
        ) from error