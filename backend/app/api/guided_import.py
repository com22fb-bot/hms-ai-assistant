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


router = APIRouter(
    prefix="/gmail/import",
    tags=["Guided mail import"],
)


class ImportStartRequest(BaseModel):
    mode: Literal["initial", "incremental"] = "initial"


def _credentials() -> tuple[Any, dict[str, Any]]:
    _, account = require_google_account()
    credentials = get_google_credentials_for_account(
        str(account["id"]),
        expected_workspace_id=str(account["workspace_id"]),
    )
    return credentials, account


@router.get("/inventory")
def import_inventory() -> dict[str, Any]:
    credentials, _ = _credentials()
    return inventory(credentials)


@router.get("/status")
def import_status() -> dict[str, Any]:
    _, account = _credentials()
    return get_guided_import_status(account)


@router.post("/start")
def import_start(payload: ImportStartRequest) -> dict[str, Any]:
    credentials, account = _credentials()

    try:
        job = start_guided_import(
            credentials=credentials,
            account=account,
            mode=payload.mode,
        )
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
    credentials, account = _credentials()
    return compare_inventory(
        credentials,
        str(account["id"]),
    )
