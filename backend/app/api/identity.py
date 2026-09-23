from __future__ import annotations

import logging
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.database.supabase import get_supabase_client
from app.security.donexto_verified import (
    can_mark_donexto_verified,
    email_is_confirmed,
    mark_donexto_verified,
    raw_user_is_trusted_verified,
    trusted_donexto_verified,
    user_from_admin_response,
    user_has_oauth_identity,
)
from app.security.identity import require_request_context
from app.security.redirect import sanitize_return_to
from app.services.donexto_verification_email import (
    VerificationEmailUserNotFound,
    resolve_verification_language,
    send_verification_email,
)


logger = logging.getLogger(__name__)


router = APIRouter(prefix="/identity", tags=["HMS Identity"])


class DonextoVerificationEmailRequest(BaseModel):
    language: str = "es"
    redirect_to: str | None = None


def _admin_user_is_trusted_verified(client: Any, user_id: str) -> bool:
    """Re-read app_metadata with the service role.

    The caller JWT can be older than ``mark_donexto_verified``. A lookup
    failure stays unverified so a new account can still receive its one mail.
    """
    try:
        record = user_from_admin_response(client.auth.admin.get_user_by_id(user_id))
    except Exception:
        logger.info("donexto_verify_admin_lookup_failed user_id=%s", user_id)
        return False
    return raw_user_is_trusted_verified(record)


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

    # The login screen sends its i18n language. Do not replace that with
    # user_metadata.language or Accept-Language: OAuth metadata often stays
    # "en" after the login strip is already Spanish.
    language = resolve_verification_language(payload.language)
    redirect_to = sanitize_return_to(payload.redirect_to)
    user_id = context.user.id if isinstance(context.user.id, str) else None

    # A trusted app_metadata flag is forever. Resend and session bootstrap
    # must not mail that account again. user_metadata is not consulted.
    if getattr(context.user, "donexto_verified", False) is True:
        logger.info("donexto_verify_skip_already_verified user_id=%s", user_id)
        return {
            "status": "ok",
            "already_verified": True,
            "donexto_verified": True,
        }

    try:
        client = get_supabase_client()
        if user_id and _admin_user_is_trusted_verified(client, user_id):
            logger.info("donexto_verify_skip_already_verified user_id=%s", user_id)
            return {
                "status": "ok",
                "already_verified": True,
                "donexto_verified": True,
            }
        send_verification_email(
            client=client,
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


_OTP_TYPES = frozenset(
    {
        "signup",
        "invite",
        "magiclink",
        "recovery",
        "email_change",
        "email",
    }
)
_TOKEN_HASH_MAX = 2048
_USED_OR_EXPIRED_DETAIL = {
    "status": "invalid_verification_token",
    "message": (
        "El enlace ya se usó o expiró. "
        "Pide otro correo y pulsa Verificar una sola vez."
    ),
}


def _used_or_expired_token() -> HTTPException:
    return HTTPException(
        status_code=403,
        detail=dict(_USED_OR_EXPIRED_DETAIL),
    )


def _safe_error_text(error: Exception) -> str:
    text = str(getattr(error, "message", None) or error)
    lowered = text.lower()
    if "bearer " in lowered or "sb_secret" in lowered or "sb_publishable" in lowered:
        return type(error).__name__
    return text[:180]


def _read(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


def _otp_types_to_try(token_type: str) -> list[str]:
    """Try the link type, then the other magic-link alias.

    ``generate_link(type=magiclink)`` stores a hashed token that current
    GoTrue verifies as ``email`` and older builds verify as ``magiclink``.
    A mismatch does not consume the token, so the second attempt is safe.
    """
    primary = token_type if token_type in _OTP_TYPES else "magiclink"
    order = [primary]
    if primary == "magiclink":
        order.append("email")
    elif primary == "email":
        order.append("magiclink")
    return order


def _verify_donexto_otp(client: Any, token_hash: str, token_type: str) -> Any:
    last_error: Exception | None = None
    for candidate in _otp_types_to_try(token_type):
        try:
            return client.auth.verify_otp(
                {"token_hash": token_hash, "type": candidate}
            )
        except Exception as error:
            last_error = error
            logger.info(
                "donexto_verify_otp_rejected type=%s error=%s",
                candidate,
                type(error).__name__,
            )
    if last_error is None:
        raise RuntimeError("verify_otp failed")
    raise last_error


def _session_tokens(verification: Any) -> dict[str, object]:
    session = _read(verification, "session")
    access = str(_read(session, "access_token") or "").strip()
    refresh = str(_read(session, "refresh_token") or "").strip()
    if not access or not refresh:
        return {}
    payload: dict[str, object] = {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
    }
    expires = _read(session, "expires_in")
    if expires is not None:
        try:
            payload["expires_in"] = int(expires)
        except (TypeError, ValueError):
            pass
    return payload


@router.post("/confirm-donexto")
def confirm_donexto_identity(request: Request) -> dict[str, object]:
    """Consume the email token and open a Donexto session.

    The Verificar link may land in a browser that has no OAuth cookie.
    ``token_hash`` is the only proof: the body and query cannot name a user,
    and OAuth alone still cannot set ``donexto_verified``.

    A call without the email flag or without the token — including the
    "Ya confirmé" button — is rejected with 403.
    """
    if request.query_params.get("donexto_verify") != "1":
        raise HTTPException(
            status_code=403,
            detail={
                "status": "donexto_verify_required",
                "message": "La confirmación debe proceder del enlace de correo Donexto.",
            },
        )

    token_hash = str(request.query_params.get("token_hash") or "").strip()
    token_type = str(request.query_params.get("type") or "magiclink").strip() or "magiclink"
    if not token_hash or len(token_hash) > _TOKEN_HASH_MAX:
        raise HTTPException(
            status_code=403,
            detail={
                "status": "verification_proof_required",
                "message": "Se requiere el token real del enlace de verificación.",
            },
        )

    client = get_supabase_client()
    try:
        verification = _verify_donexto_otp(client, token_hash, token_type)
    except Exception as error:
        raise _used_or_expired_token() from error

    user_id = str(_read(_read(verification, "user"), "id") or "").strip()
    try:
        UUID(user_id)
    except ValueError as error:
        raise HTTPException(
            status_code=403,
            detail={
                "status": "invalid_verification_token",
                "message": "El enlace de verificación es inválido o ha expirado.",
            },
        ) from error

    try:
        response = client.auth.admin.get_user_by_id(user_id)
    except Exception as error:
        logger.error(
            "donexto_verify_admin_lookup_failed user_id=%s error=%s message=%s",
            user_id,
            type(error).__name__,
            _safe_error_text(error),
        )
        raise _used_or_expired_token() from error
    raw_user = _read(response, "user")
    if raw_user is None:
        raise HTTPException(
            status_code=403,
            detail={
                "status": "invalid_verification_token",
                "message": "El enlace de verificación es inválido o ha expirado.",
            },
        )

    app_metadata = _read(raw_user, "app_metadata")
    if not isinstance(app_metadata, dict):
        app_metadata = {}
    user_metadata = _read(raw_user, "user_metadata")
    if not isinstance(user_metadata, dict):
        user_metadata = {}
    oauth_identity = user_has_oauth_identity(
        identities=_read(raw_user, "identities"),
        user_metadata=user_metadata,
        app_metadata=app_metadata,
    )
    already = trusted_donexto_verified(
        app_metadata,
        oauth_identity_present=oauth_identity,
    )
    if not already:
        verified_user = _read(verification, "user")
        if not (
            can_mark_donexto_verified(raw_user)
            or email_is_confirmed(verified_user)
        ):
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
        try:
            mark_donexto_verified(user_id)
        except Exception as error:
            logger.error(
                "donexto_verify_mark_failed user_id=%s error=%s message=%s",
                user_id,
                type(error).__name__,
                _safe_error_text(error),
            )
            raise _used_or_expired_token() from error

    payload: dict[str, object] = {
        "status": "ok",
        "donexto_verified": True,
        "already": already,
    }
    payload.update(_session_tokens(verification))
    logger.info(
        "donexto_verify_confirm result=ok user_id=%s already=%s has_session=%s",
        user_id,
        already,
        "access_token" in payload,
    )
    return payload


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
