from __future__ import annotations

from fastapi import APIRouter, HTTPException

from pydantic import BaseModel, Field
from app.security.mailbox_verification import (
    context_verified, request_verification, confirm_verification,
)
from app.security.identity import require_request_context


router = APIRouter(prefix="/identity", tags=["HMS Identity"])


@router.get("/me")
def identity_me() -> dict[str, object]:
    context = require_request_context()
    account = context.google_account

    return {
        "status": "ok",
        "user": {
            "id": context.user.id,
            "email": context.user.email,
            "full_name": context.user.full_name,
            "donexto_verified": context_verified(context),
            "has_oauth_identity": context.user.has_oauth_identity,
        },
        "workspace": {
            "id": context.workspace_id,
            "name": context.workspace_name,
            "role": context.membership_role,
        },
        "mailbox": (
            {
                "connected": True,
                "id": str(account.get("id")),
                "provider": account.get("provider"),
                "email": account.get("email"),
                "display_name": account.get("display_name"),
                "status": account.get("status"),
            }
            if account
            else {
                "connected": False,
                "provider": None,
                "email": None,
            }
        ),
    }


class VerifyMailboxRequest(BaseModel):
    token: str = Field(min_length=32, max_length=128)


@router.post("/request-verification")
def request_mailbox_verification() -> dict:
    return request_verification(require_request_context())


@router.post("/confirm-donexto")
def confirm_donexto_identity(payload: VerifyMailboxRequest) -> dict:
    return confirm_verification(require_request_context(), payload.token)


def require_donexto_verified_for_context() -> None:
    if not context_verified(require_request_context()):
        raise HTTPException(403, detail={
            "status": "donexto_unverified",
            "message": "Abre el enlace enviado al correo que deseas monitorear.",
        })
