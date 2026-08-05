from __future__ import annotations

from fastapi import APIRouter

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
