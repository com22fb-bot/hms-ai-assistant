from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Query
from google.oauth2.credentials import Credentials

from app.schemas.gmail import GmailMessagesResponse
from app.security.identity import require_google_account
from app.security.mutation_guard import require_data_mutations_enabled
from app.services.case_engine import process_pending_messages
from app.services.gmail import list_messages
from app.services.gmail_full_sync import sync_gmail_page
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
        limit: int = Query(default=20, ge=1, le=100),
        query: str | None = Query(default=None),
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

    @router.post("/sync")
    def gmail_sync(
        limit: int = Query(default=100, ge=1, le=500),
        query: str | None = Query(default=None),
        process_cases: bool = Query(default=True),
    ) -> dict[str, Any]:
        require_data_mutations_enabled("gmail_sync")
        credentials = get_credentials()
        _, account = require_google_account()

        sync_result = sync_gmail_messages(
            credentials=credentials,
            limit=limit,
            query=query,
            account_id=str(account["id"]),
        )

        result: dict[str, Any] = {
            "status": sync_result.get("status", "ok"),
            "sync": sync_result,
        }

        if process_cases:
            result["case_engine"] = process_pending_messages(
                limit=limit,
                account_id=str(account["id"]),
                workspace_id=str(account["workspace_id"]),
            )

        return result

    @router.post("/sync-all")
    def gmail_sync_all(
        batch_size: int = Query(
            default=500,
            ge=1,
            le=500,
        ),
        page_token: str | None = Query(default=None),
        query: str | None = Query(default=None),
        process_cases: bool = Query(default=True),
    ) -> dict[str, Any]:
        require_data_mutations_enabled("gmail_sync_all")
        credentials = get_credentials()
        _, account = require_google_account()

        sync_result = sync_gmail_page(
            credentials=credentials,
            batch_size=batch_size,
            page_token=page_token,
            query=query,
            account_id=str(account["id"]),
        )

        result: dict[str, Any] = {
            "status": sync_result.get("status", "ok"),
            "sync": sync_result,
        }

        if process_cases:
            result["case_engine"] = process_pending_messages(
                limit=batch_size,
                account_id=str(account["id"]),
                workspace_id=str(account["workspace_id"]),
            )

        return result

    return router
