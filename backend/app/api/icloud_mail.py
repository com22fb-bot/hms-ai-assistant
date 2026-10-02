"""Conexión de iCloud Mail: contraseña específica de app, solo lectura.

Donexto lee únicamente el correo que el usuario autoriza. La contraseña
de app se guarda cifrada (OAUTH_ENCRYPTION_KEY) y se borra al desconectar.
Nunca se escribe en logs ni en el detalle de un error.
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
from app.services.icloud_imap import (
    IcloudImapError,
    is_icloud_address,
    normalize_icloud_address,
    stored_icloud_uses_app_password,
    verify_icloud_login,
)
from app.services.imap_provider import ICLOUD_IMAP
from app.services.oauth_storage import (
    OAuthCredentialError,
    OAuthStorageError,
    oauth_storage,
)
from app.services.yahoo_session import mint_yahoo_session_or_http


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/icloud", tags=["iCloud Mail"])

_SIGNUP_VIA = "icloud_imap"


class IcloudConnectRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    app_password: str = Field(min_length=1, max_length=256)


class IcloudConnectResponse(BaseModel):
    connected: bool = True
    email: str
    provider: str = "icloud"
    message: str
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str | None = None
    expires_in: int | None = None


def _http_from_imap(error: IcloudImapError) -> HTTPException:
    return HTTPException(
        status_code=400,
        detail={
            "status": "icloud_auth_failed",
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
                "message": "Confirma tu correo Donexto antes de conectar iCloud.",
            },
        )
    return resolve_workspace_context(request, user)


def persist_icloud_mailbox(
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
            "provider", "icloud"
        ).execute()
    except Exception:
        logger.info(
            "No se pudieron pausar otros buzones del workspace %s",
            workspace_id,
        )

    try:
        account = oauth_storage.upsert_communication_account(
            provider="icloud",
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
            token_uri=f"imap://{ICLOUD_IMAP.host}:{ICLOUD_IMAP.port}",
            scopes=["imap", "readonly"],
            metadata={
                "protocol": "imap",
                "auth": "app_password",
                "host": ICLOUD_IMAP.host,
                "port": ICLOUD_IMAP.port,
                "readonly": True,
                "connected_by_profile_id": user_id,
                "workspace_id": workspace_id,
            },
        )
    except (OAuthStorageError, OAuthCredentialError) as error:
        logger.exception("No se pudo guardar la conexión iCloud de %s", address)
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "iCloud autenticó, pero no se pudo guardar la conexión.",
            },
        ) from error


@router.post("/connect", response_model=IcloudConnectResponse)
def icloud_connect(
    payload: IcloudConnectRequest,
    request: Request,
) -> IcloudConnectResponse:
    client_host = getattr(getattr(request, "client", None), "host", None) or "unknown"
    if not allow_request(f"icloud-connect:{client_host}", max_requests=8, window_seconds=60):
        raise HTTPException(
            status_code=429,
            detail={
                "status": "rate_limited",
                "code": "rate_limited",
                "message": "Demasiados intentos seguidos. Espera un momento.",
            },
        )

    address = normalize_icloud_address(payload.email)
    if not is_icloud_address(address):
        raise HTTPException(
            status_code=400,
            detail={
                "status": "icloud_auth_failed",
                "code": "invalid_address",
                "message": (
                    "Indica el correo completo de iCloud "
                    "(@icloud.com, @me.com o @mac.com)."
                ),
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
                    "Usa el mismo iCloud con el que entraste."
                ),
            },
        )

    try:
        verified = verify_icloud_login(address, payload.app_password)
    except IcloudImapError as error:
        raise _http_from_imap(error) from error

    access_token = None
    refresh_token = None
    expires_in = None
    if context is None:
        session = mint_yahoo_session_or_http(
            verified,
            allow_create=True,
            signup_via=_SIGNUP_VIA,
            provider_label="iCloud",
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

    from app.services.icloud_imap import normalize_icloud_app_password

    persist_icloud_mailbox(
        user_id=user_id,
        workspace_id=workspace_id,
        address=verified,
        app_password=normalize_icloud_app_password(payload.app_password),
    )
    logger.info("Buzón iCloud conectado en solo lectura para %s", verified)
    return IcloudConnectResponse(
        connected=True,
        email=verified,
        message=(
            "iCloud conectado en solo lectura. Donexto no marca tus correos "
            "como leídos ni los mueve. Puedes revocar la contraseña de app "
            "en Apple cuando quieras."
        ),
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer" if access_token else None,
        expires_in=expires_in,
    )


@router.get("/status", response_model=GoogleConnectionStatus)
def icloud_status() -> GoogleConnectionStatus:
    context = require_request_context()
    account = context.google_account
    if not account or str(account.get("provider") or "") != "icloud":
        return GoogleConnectionStatus(
            connected=False,
            provider="icloud",
            message="No hay buzón iCloud activo en este espacio.",
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
        provider="icloud",
        has_access_token=has_secret,
        has_refresh_token=False,
        scopes=list((credentials or {}).get("scopes") or []),
        message=(
            "Buzón iCloud conectado en solo lectura."
            if has_secret
            else "Falta volver a conectar iCloud."
        ),
        login_url=None,
        mail_read_available=has_secret,
    )


@router.post("/disconnect", response_model=GoogleConnectionStatus)
def icloud_disconnect() -> GoogleConnectionStatus:
    context = require_request_context()
    account = context.google_account
    if not account or str(account.get("provider") or "") != "icloud":
        return GoogleConnectionStatus(
            connected=False,
            provider="icloud",
            message="No había buzón iCloud que desconectar.",
        )
    oauth_storage.disconnect_account(str(account["id"]), delete_credentials=True)
    logger.info("Buzón iCloud desconectado para %s", account.get("email"))
    return GoogleConnectionStatus(
        connected=False,
        provider="icloud",
        message="Buzón iCloud desconectado. La contraseña de app ya no está guardada.",
    )
