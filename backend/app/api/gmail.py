from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Query
from google.oauth2.credentials import Credentials

from app.schemas.gmail import GmailMessagesResponse
from app.services.gmail import list_messages
from app.services.gmail_sync import sync_gmail_messages


CredentialsProvider = Callable[[], Credentials]


def create_gmail_router(
    get_credentials: CredentialsProvider,
) -> APIRouter:
    """
    Crea el router de Gmail.

    La función que obtiene las credenciales se recibe desde main.py
    para evitar dependencias circulares.
    """

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
                "Cantidad máxima de correos que se consultarán."
            ),
        ),
        query: str | None = Query(
            default=None,
            description=(
                "Consulta opcional utilizando la sintaxis "
                "de búsqueda de Gmail."
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
                "Cantidad máxima de mensajes que se sincronizarán."
            ),
        ),
        query: str | None = Query(
            default=None,
            description=(
                "Consulta opcional con sintaxis de Gmail. "
                "Cuando se omite, se utiliza last_sync_at."
            ),
        ),
    ) -> dict[str, Any]:
        credentials = get_credentials()

        return sync_gmail_messages(
            credentials=credentials,
            limit=limit,
            query=query,
        )

    return router
