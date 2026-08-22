from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.auth import get_google_credentials_for_account
from app.security.identity import require_google_account
from app.services.gmail_import_inventory import (
    compare_inventory,
    inventory,
)
from app.services.guided_import_job_service import (
    get_guided_import_status,
    start_guided_import,
)
from app.services.oauth_storage import oauth_storage
from app.services.yahoo_imap import YahooImapError, stored_yahoo_uses_oauth
from app.services.yahoo_import import is_yahoo_provider, yahoo_inventory
from app.services.microsoft_import import (
    MicrosoftImportError,
    is_microsoft_provider,
    microsoft_inventory,
)


router = APIRouter(
    prefix="/gmail/import",
    tags=["Guided mail import"],
)


class ImportStartRequest(BaseModel):
    mode: Literal["initial", "incremental"] = "initial"


def _mailbox_account() -> dict[str, Any]:
    _, account = require_google_account()
    return account


def _google_credentials(account: dict[str, Any]) -> Any:
    return get_google_credentials_for_account(
        str(account["id"]),
        expected_workspace_id=str(account["workspace_id"]),
    )


def _yahoo_secret(account: dict[str, Any]) -> tuple[str, str, bool]:
    credentials = oauth_storage.get_credentials(str(account["id"]))
    token = str((credentials or {}).get("access_token") or "")
    email = str(account.get("email") or "")
    if not token or not email or not stored_yahoo_uses_oauth(credentials):
        raise HTTPException(
            status_code=401,
            detail={
                "status": "yahoo_required",
                "message": (
                    "Vuelve a autorizar Yahoo en el sitio de Yahoo. "
                    "Donexto no pide tu clave."
                ),
            },
        )
    return email, token, True


@router.get("/inventory")
def import_inventory() -> dict[str, Any]:
    account = _mailbox_account()
    if is_yahoo_provider(account):
        email, app_password, oauth = _yahoo_secret(account)
        try:
            return yahoo_inventory(email, app_password, oauth=oauth)
        except YahooImapError as error:
            raise HTTPException(
                status_code=400,
                detail={
                    "status": "yahoo_inventory_failed",
                    "message": str(error),
                },
            ) from error
    if is_microsoft_provider(account):
        try:
            return microsoft_inventory(account)
        except MicrosoftImportError as error:
            raise HTTPException(
                status_code=400,
                detail={
                    "status": "microsoft_inventory_failed",
                    "message": str(error),
                },
            ) from error
    return inventory(_google_credentials(account))


@router.get("/status")
def import_status() -> dict[str, Any]:
    return get_guided_import_status(_mailbox_account())


@router.post("/start")
def import_start(payload: ImportStartRequest) -> dict[str, Any]:
    account = _mailbox_account()
    credentials = None
    if not is_yahoo_provider(account) and not is_microsoft_provider(account):
        credentials = _google_credentials(account)

    try:
        job = start_guided_import(
            credentials=credentials,
            account=account,
            mode=payload.mode,
        )
    except YahooImapError as error:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "yahoo_import_failed",
                "message": str(error),
            },
        ) from error
    except MicrosoftImportError as error:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "microsoft_import_failed",
                "message": str(error),
            },
        ) from error
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "status": "invalid_guided_import",
                "message": str(exc),
            },
        ) from exc

    return {
        "status": "ok",
        "job": job,
    }


@router.get("/compare")
def import_compare() -> dict[str, Any]:
    account = _mailbox_account()
    if is_yahoo_provider(account) or is_microsoft_provider(account):
        raise HTTPException(
            status_code=409,
            detail={
                "status": "compare_gmail_only",
                "message": "La comparación de inventario aplica a Gmail.",
            },
        )
    return compare_inventory(
        _google_credentials(account),
        str(account["id"]),
    )
