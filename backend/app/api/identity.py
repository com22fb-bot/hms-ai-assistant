from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.database.supabase import get_supabase_client
from app.security.donexto_verified import (
    can_mark_donexto_verified,
    mark_donexto_verified,
)
from app.security.identity import require_request_context
from app.security.redirect import sanitize_return_to
from app.services.donexto_verification_email import send_verification_email
from app.services.support_notify import SMTPDeliveryError


router = APIRouter(prefix="/identity", tags=["HMS Identity"])


class DonextoVerificationEmailRequest(BaseModel):
    language: str = "es"
    redirect_to: str | None = None


def _append_verify_flag(url: str) -> str:
    """Append ``donexto_verify=1`` preserving any pre-existing query string.

    The old ``f"{url}?donexto_verify=1"`` concatenation broke URLs that
    already had a query string (produced malformed ``?a=b?donexto_verify=1``
    which Supabase then propagated back verbatim).
    """
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["donexto_verify"] = "1"
    return urlunparse(parsed._replace(query=urlencode(query)))


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


@router.post("/send-donexto-verify")
def send_donexto_verification_email(
    payload: DonextoVerificationEmailRequest,
) -> dict[str, object]:
    """Request a Donexto verification email. Requires an authenticated session.

    Never accepts an email from the request body. The only source of truth
    is the authenticated user's email from the session context.
    """
    context = require_request_context()
    email = (context.user.email or "").strip().lower()
    if not email:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "verification_email_missing_email",
                "message": "Falta el correo de la cuenta Donexto.",
            },
        )

    language = payload.language or context.user.raw_user_metadata.get(
        "language", "es"
    )
    redirect_to = sanitize_return_to(payload.redirect_to)
    try:
        message = send_verification_email(
            client=get_supabase_client(),
            email=email,
            language=language,
            redirect_to=_append_verify_flag(redirect_to),
        )
    except SMTPDeliveryError as error:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "verification_email_delivery_failed",
                "message": "No fue posible enviar el correo de verificación.",
                "error_type": error.error_type,
            },
        ) from error
    except (RuntimeError, ValueError) as error:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "verification_email_unavailable",
                "message": "No fue posible preparar el correo de verificación.",
            },
        ) from error
    return {"status": "sent", "language": language, "subject": message.subject}


@router.post("/confirm-donexto")
def confirm_donexto_identity(request: Request) -> dict[str, object]:
    """Mark Donexto email verification from a trusted source (service role only).

    Clients must not write ``donexto_verified`` via ``updateUser`` — that field
    lives in ``app_metadata`` and is set here after confirmed email.

    Requires the real ``?donexto_verify=1`` query flag that only the email
    link carries. A hand-crafted call or the "Ya confirmé mi correo" button
    without the flag is rejected with 403.
    """
    if request.query_params.get("donexto_verify") != "1":
        raise HTTPException(
            status_code=403,
            detail={
                "status": "donexto_verify_required",
                "message": "La confirmación debe proceder del enlace de correo Donexto.",
            },
        )

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
                    "que enviamos a tu correo Donexto."
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
    if context.user.donexto_verified:
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
