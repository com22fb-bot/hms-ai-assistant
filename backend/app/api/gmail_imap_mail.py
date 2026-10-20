"""Conexión de Gmail por IMAP con contraseña de aplicación, solo lectura.

Alternativa a Google OAuth (sin verificación CASA). Servidor imap.gmail.com:993
SSL. El login se valida antes de guardar. La contraseña de aplicación se guarda
cifrada (OAUTH_ENCRYPTION_KEY) y se borra al desconectar. Nunca se escribe en
logs ni en el detalle de un error. La sincronización usa el mismo pipeline IMAP
que iCloud y Yahoo.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.schemas.gmail import GoogleConnectionStatus
from app.security.identity import (
    authenticate_request,
    require_request_context,
    resolve_workspace_context,
)
from app.security.rate_limit import allow_request
from app.services.gmail_imap import (
    GmailImapError,
    normalize_gmail_address,
    normalize_gmail_app_password,
    verify_gmail_imap_login,
)
from app.services.icloud_imap import stored_icloud_uses_app_password
from app.services.imap_provider import GMAIL_IMAP
from app.services.oauth_storage import (
    OAuthCredentialError,
    OAuthStorageError,
    oauth_storage,
)
from app.services.yahoo_session import mint_yahoo_session_or_http


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/gmail-imap", tags=["Gmail IMAP"])

_SIGNUP_VIA = "gmail_imap"


class GmailImapConnectRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    app_password: str = Field(min_length=1, max_length=256)


class GmailImapConnectResponse(BaseModel):
    connected: bool = True
    email: str
    provider: str = "gmail_imap"
    message: str
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str | None = None
    expires_in: int | None = None


def _http_from_imap(error: GmailImapError) -> HTTPException:
    return HTTPException(
        status_code=400,
        detail={
            "status": "gmail_imap_auth_failed",
            "code": error.code,
            "message": str(error),
        },
    )


def _session_if_present(request: Request):
    authorization = request.headers.get("authorization", "").strip()
    if not authorization:
        return None
    user = authenticate_request(request)
    if not user.donexto_verified:
        raise HTTPException(
            status_code=403,
            detail={
                "status": "donexto_unverified",
                "message": "Confirma tu correo Donexto antes de conectar Gmail.",
            },
        )
    return resolve_workspace_context(request, user)


def persist_gmail_imap_mailbox(
    *,
    user_id: str,
    workspace_id: str,
    address: str,
    app_password: str,
) -> None:
    """Guarda la contraseña de app cifrada. El argumento no se registra."""
    try:
        oauth_storage.client.table("communication_accounts").update(
            {"status": "inactive"}
        ).eq("workspace_id", workspace_id).eq("status", "active").neq(
            "provider", "gmail_imap"
        ).execute()
    except Exception:
        logger.info(
            "No se pudieron pausar otros buzones del workspace %s",
            workspace_id,
        )

    try:
        account = oauth_storage.upsert_communication_account(
            provider="gmail_imap",
            provider_account_id=address,
            email=address,
            display_name=address,
            workspace_id=workspace_id,
            connected_by_profile_id=user_id,
            status="active",
        )
        oauth_storage.save_credentials(
            account_id=account["id"],
            access_token=app_password,
            refresh_token=None,
            token_uri=f"imap://{GMAIL_IMAP.host}:{GMAIL_IMAP.port}",
            scopes=["imap", "readonly"],
            metadata={
                "protocol": "imap",
                "auth": "app_password",
                "host": GMAIL_IMAP.host,
                "port": GMAIL_IMAP.port,
                "readonly": True,
                "connected_by_profile_id": user_id,
                "workspace_id": workspace_id,
            },
        )
    except (OAuthStorageError, OAuthCredentialError) as error:
        logger.exception("No se pudo guardar la conexión Gmail de %s", address)
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "Gmail autenticó, pero no se pudo guardar la conexión.",
            },
        ) from error


@router.post("/connect", response_model=GmailImapConnectResponse)
def gmail_imap_connect(
    payload: GmailImapConnectRequest,
    request: Request,
) -> GmailImapConnectResponse:
    client_host = getattr(getattr(request, "client", None), "host", None) or "unknown"
    if not allow_request(f"gmail-imap-connect:{client_host}", max_requests=8, window_seconds=60):
        raise HTTPException(
            status_code=429,
            detail={
                "status": "rate_limited",
                "code": "rate_limited",
                "message": "Demasiados intentos seguidos. Espera un momento.",
            },
        )

    address = normalize_gmail_address(payload.email)
    if "@" not in address or "." not in address.rsplit("@", 1)[-1]:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "gmail_imap_auth_failed",
                "code": "invalid_address",
                "message": "Indica el correo completo de Gmail.",
            },
        )

    context = _session_if_present(request)
    if context is not None and address != context.user.email.strip().lower():
        raise HTTPException(
            status_code=403,
            detail={
                "status": "email_mismatch",
                "code": "email_mismatch",
                "message": (
                    "Donexto solo lee el correo de esta cuenta. "
                    "Usa el mismo Gmail con el que entraste."
                ),
            },
        )

    try:
        verified = verify_gmail_imap_login(address, payload.app_password)
    except GmailImapError as error:
        # Solo el código y la respuesta del servidor ya sin secreto; nunca la contraseña.
        logger.warning(
            "Gmail IMAP rechazó el acceso de %s: code=%s server=%r",
            address,
            error.code,
            getattr(error, "server_text", "") or "",
        )
        raise _http_from_imap(error) from error

    access_token = None
    refresh_token = None
    expires_in = None
    if context is None:
        session = mint_yahoo_session_or_http(
            verified,
            allow_create=True,
            signup_via=_SIGNUP_VIA,
            provider_label="Gmail",
        )
        user_id = str(session["user_id"])
        workspace_id = str(session["workspace_id"])
        access_token = str(session.get("access_token") or "") or None
        refresh_token = str(session.get("refresh_token") or "") or None
        raw_expires = session.get("expires_in")
        if raw_expires is not None:
            try:
                expires_in = int(raw_expires)
            except (TypeError, ValueError):
                expires_in = None
    else:
        user_id = context.user.id
        workspace_id = context.workspace_id

    persist_gmail_imap_mailbox(
        user_id=user_id,
        workspace_id=workspace_id,
        address=verified,
        app_password=normalize_gmail_app_password(payload.app_password),
    )
    logger.info("Buzón Gmail conectado en solo lectura para %s", verified)
    return GmailImapConnectResponse(
        connected=True,
        email=verified,
        message=(
            "Gmail conectado en solo lectura. Donexto no marca tus correos "
            "como leídos ni los mueve. Puedes revocar la contraseña de "
            "aplicación en tu cuenta de Google cuando quieras."
        ),
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer" if access_token else None,
        expires_in=expires_in,
    )


@router.get("/status", response_model=GoogleConnectionStatus)
def gmail_imap_status() -> GoogleConnectionStatus:
    context = require_request_context()
    account = context.google_account
    if not account or str(account.get("provider") or "") != "gmail_imap":
        return GoogleConnectionStatus(
            connected=False,
            provider="gmail_imap",
            message="No hay buzón Gmail activo en este espacio.",
            login_url=None,
        )
    credentials = oauth_storage.get_credentials(str(account["id"]))
    has_secret = bool(
        credentials
        and credentials.get("access_token")
        and stored_icloud_uses_app_password(credentials)
    )
    return GoogleConnectionStatus(
        connected=has_secret,
        email=account.get("email"),
        provider="gmail_imap",
        has_access_token=has_secret,
        has_refresh_token=False,
        scopes=list((credentials or {}).get("scopes") or []),
        message=(
            "Buzón Gmail conectado en solo lectura."
            if has_secret
            else "Falta volver a conectar Gmail."
        ),
        login_url=None,
        mail_read_available=has_secret,
    )


@router.post("/disconnect", response_model=GoogleConnectionStatus)
def gmail_imap_disconnect() -> GoogleConnectionStatus:
    context = require_request_context()
    account = context.google_account
    if not account or str(account.get("provider") or "") != "gmail_imap":
        return GoogleConnectionStatus(
            connected=False,
            provider="gmail_imap",
            message="No había buzón Gmail que desconectar.",
        )
    oauth_storage.disconnect_account(str(account["id"]), delete_credentials=True)
    logger.info("Buzón Gmail desconectado para %s", account.get("email"))
    return GoogleConnectionStatus(
        connected=False,
        provider="gmail_imap",
        message="Gmail desconectado. La contraseña de aplicación ya no está guardada.",
    )
