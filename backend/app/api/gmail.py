from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Query
from google.oauth2.credentials import Credentials

from app.schemas.gmail import GmailMessagesResponse
from app.services.gmail import list_messages


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

    return router
