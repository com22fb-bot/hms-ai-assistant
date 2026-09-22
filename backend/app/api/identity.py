from __future__ import annotations

import logging
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
from app.services.donexto_verification_email import (
    VerificationEmailUserNotFound,
    send_verification_email,
)


logger = logging.getLogger(__name__)


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
    user_id = context.user.id if isinstance(context.user.id, str) else None
    try:
        send_verification_email(
            client=get_supabase_client(),
            email=email,
            language=language,
            redirect_to=_append_verify_flag(redirect_to),
            user_id=user_id,
        )
    except VerificationEmailUserNotFound:
        # Public response never reveals whether the account exists.
        logger.info("donexto_verify_resend_unknown_user user_id=%s", context.user.id)
        return {"status": "sent"}
    except Exception as error:
        logger.error(
            "donexto_verify_resend_provider_error user_id=%s",
            context.user.id,
            exc_info=True,
        )
        raise HTTPException(
            status_code=503,
            detail={
                "code": "verification_email_delivery_failed",
                "message": (
                    "No pudimos enviar el correo de confirmación de Donexto. "
                    "Pulsa Reenviar en un momento."
                ),
            },
        ) from error
    return {"status": "sent"}


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

    token_hash = request.query_params.get("token_hash")
    token_type = request.query_params.get("type") or "signup"
    if not token_hash:
        raise HTTPException(
            status_code=403,
            detail={
                "status": "verification_proof_required",
                "message": "Se requiere el token real del enlace de verificación.",
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
    try:
        verification = client.auth.verify_otp(
            {"token_hash": token_hash, "type": token_type}
        )
    except Exception as error:
        raise HTTPException(
            status_code=403,
            detail={
                "status": "invalid_verification_token",
                "message": "El enlace de verificación es inválido o ha expirado.",
            },
        ) from error

    verified_user = getattr(verification, "user", None)
    if verified_user is None and isinstance(verification, dict):
        verified_user = verification.get("user")
    verified_user_id = getattr(verified_user, "id", None)
    if verified_user_id is None and isinstance(verified_user, dict):
        verified_user_id = verified_user.get("id")
    if str(verified_user_id or "") != context.user.id:
        raise HTTPException(
            status_code=403,
            detail={
                "status": "verification_user_mismatch",
                "message": "El enlace no pertenece a la sesión Donexto actual.",
            },
        )

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
