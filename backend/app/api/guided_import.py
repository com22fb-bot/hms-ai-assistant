from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.auth import get_google_credentials_for_account
from app.security.identity import require_google_account
from app.services.gmail_import_inventory import (
    compare_inventory,
    inventory,
    preview,
)


router = APIRouter(
    prefix="/gmail/import",
    tags=["Gmail guided inventory"],
)


class ImportSelectionRequest(BaseModel):
    categories: list[str] = Field(min_length=1)


class ImportStartRequest(ImportSelectionRequest):
    confirmation: str | None = None
    batch_size: int = Field(default=100, ge=25, le=100)


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


@router.post("/preview")
def import_preview(
    payload: ImportSelectionRequest,
) -> dict[str, Any]:
    credentials, _ = _credentials()

    try:
        return preview(credentials, payload.categories)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


@router.get("/compare")
def import_compare() -> dict[str, Any]:
    credentials, account = _credentials()
    return compare_inventory(
        credentials,
        str(account["id"]),
    )


@router.post("/start")
def import_start_blocked(
    payload: ImportStartRequest,
) -> dict[str, Any]:
    del payload
    _credentials()

    raise HTTPException(
        status_code=423,
        detail={
            "status": "inventory_review_required",
            "message": (
                "La importación histórica permanece bloqueada hasta "
                "revisar el inventario y aprobar la limpieza controlada."
            ),
        },
    )


@router.get("/status")
def import_status() -> dict[str, Any]:
    _credentials()
    return {
        "status": "inventory_only",
        "active": None,
        "latest": None,
        "import_enabled": False,
        "message": (
            "Inventario disponible. Importación y limpieza bloqueadas."
        ),
    }
