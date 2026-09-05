from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.database.supabase import get_supabase_client
from app.security.donexto_verified import (
    can_mark_donexto_verified,
    mark_donexto_verified,
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
            "donexto_verified": context.user.donexto_verified,
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


@router.post("/confirm-donexto")
def confirm_donexto_identity() -> dict[str, object]:
    """Mark Donexto email verification from a trusted source (service role only).

    Clients must not write ``donexto_verified`` via ``updateUser`` — that field
    lives in ``app_metadata`` and is set here after OAuth or confirmed email.
    """
    context = require_request_context()
    if context.user.donexto_verified:
        return {
            "status": "ok",
            "donexto_verified": True,
            "already": True,
        }

    client = get_supabase_client()
    response = client.auth.admin.get_user_by_id(context.user.id)
    raw_user = getattr(response, "user", None)
    if raw_user is None and isinstance(response, dict):
        raw_user = response.get("user")

    if not can_mark_donexto_verified(raw_user):
        raise HTTPException(
            status_code=403,
            detail={
                "status": "donexto_unverified",
                "message": (
                    "Aún no podemos confirmar ese correo. Abre el enlace "
                    "que enviamos o inicia sesión con Yahoo, Google o Microsoft."
                ),
            },
        )

    mark_donexto_verified(context.user.id)
    return {
        "status": "ok",
        "donexto_verified": True,
        "already": False,
    }


def require_donexto_verified_for_context() -> None:
    context = require_request_context()
    if context.user.donexto_verified or context.user.has_oauth_identity:
        return
    raise HTTPException(
        status_code=403,
        detail={
            "status": "donexto_unverified",
            "message": (
                "Confirma tu correo Donexto antes de continuar. "
                "Revisa la bandeja o vuelve a iniciar sesión."
            ),
        },
    )
