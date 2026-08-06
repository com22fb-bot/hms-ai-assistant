from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.security.identity import (
    authenticate_request,
    get_request_context_or_none,
    reset_request_context,
    resolve_workspace_context,
    set_request_context,
)
from app.services.reclassification_service import (
    get_reclassification_status,
    start_reclassification,
)


router = APIRouter(
    prefix="/reclassification",
    tags=["Intelligent Reclassification"],
)


class ReclassificationStartRequest(BaseModel):
    confirmation: str


ResultType = TypeVar("ResultType")


def _execute_with_hms_context(
    request: Request,
    operation: Callable[[], ResultType],
) -> ResultType:
    """
    Garantiza que las rutas de reclasificación tengan una identidad HMS.

    Si el middleware ya estableció el contexto, lo reutiliza. Si la ruta
    llegó sin contexto, valida directamente el bearer token enviado por
    el frontend y resuelve el workspace y la cuenta conectada.
    """

    if get_request_context_or_none() is not None:
        return operation()

    user = authenticate_request(request)
    context = resolve_workspace_context(
        request,
        user,
    )
    context_token = set_request_context(context)

    try:
        return operation()
    finally:
        reset_request_context(context_token)


@router.get("/status")
def reclassification_status(
    request: Request,
) -> dict[str, Any]:
    return _execute_with_hms_context(
        request,
        get_reclassification_status,
    )


@router.post("/start")
def reclassification_start(
    payload: ReclassificationStartRequest,
    request: Request,
) -> dict[str, Any]:
    if payload.confirmation.strip().upper() != "RECLASIFICAR":
        raise HTTPException(
            status_code=422,
            detail={
                "status": "confirmation_required",
                "message": (
                    "Confirma la prueba escribiendo RECLASIFICAR."
                ),
            },
        )

    return _execute_with_hms_context(
        request,
        lambda: {
            "status": "ok",
            "run": start_reclassification(),
        },
    )
