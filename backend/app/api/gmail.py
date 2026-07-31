from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Query
from google.oauth2.credentials import Credentials

from app.schemas.gmail import GmailMessagesResponse
from app.services.case_engine import process_pending_messages
from app.services.gmail import list_messages
from app.services.gmail_sync import sync_gmail_messages


CredentialsProvider = Callable[[], Credentials]


def create_gmail_router(
    get_credentials: CredentialsProvider,
) -> APIRouter:
    router = APIRouter(
        prefix="/gmail",
        tags=["Gmail"],
    )

    @router.get(
        "/messages",
        response_model=GmailMessagesResponse,
    )
    def gmail_messages(
        limit: int = Query(
            default=20,
            ge=1,
            le=100,
            description=(
                "Cantidad máxima de correos consultados "
                "directamente en Gmail."
            ),
        ),
        query: str | None = Query(
            default=None,
            description=(
                "Consulta opcional con sintaxis de Gmail."
            ),
        ),
    ) -> GmailMessagesResponse:
        credentials = get_credentials()

        messages = list_messages(
            credentials=credentials,
            max_results=limit,
            query=query,
        )

        return GmailMessagesResponse(
            total=len(messages),
            messages=messages,
        )

    @router.post(
        "/sync",
        response_model=None,
    )
    def gmail_sync(
        limit: int = Query(
            default=100,
            ge=1,
            le=500,
            description=(
                "Cantidad máxima de mensajes sincronizados."
            ),
        ),
        query: str | None = Query(
            default=None,
            description=(
                "Consulta opcional con sintaxis de Gmail. "
                "Cuando se omite se utiliza last_sync_at."
            ),
        ),
        process_cases: bool = Query(
            default=True,
            description=(
                "Procesa automáticamente los mensajes "
                "sincronizados dentro del Case Engine."
            ),
        ),
    ) -> dict[str, Any]:
        credentials = get_credentials()

        sync_result = sync_gmail_messages(
            credentials=credentials,
            limit=limit,
            query=query,
        )

        result: dict[str, Any] = {
            "status": sync_result.get("status", "ok"),
            "sync": sync_result,
        }

        if process_cases:
            result["case_engine"] = process_pending_messages(
                limit=limit,
            )

        return result

    return router
