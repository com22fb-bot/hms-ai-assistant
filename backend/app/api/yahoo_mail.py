"""Conexión de Yahoo Mail (IMAP con correo y clave de Yahoo)."""

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.schemas.gmail import GoogleConnectionStatus
from app.security.identity import require_request_context
from app.services.oauth_storage import (
    OAuthCredentialError,
    OAuthStorageError,
    oauth_storage,
)
from app.services.yahoo_imap import (
    YahooImapError,
    normalize_yahoo_address,
    normalize_yahoo_app_password,
    verify_yahoo_login,
)
from app.services.yahoo_session import mint_yahoo_session_or_http


router = APIRouter(prefix="/auth/yahoo", tags=["Yahoo Mail"])

_ENTER_WINDOW_SECONDS = 15 * 60
_ENTER_MAX_ATTEMPTS = 8
_enter_attempts: dict[str, list[float]] = {}


class YahooConnectRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    app_password: str = Field(min_length=6, max_length=256)


class YahooEnterResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int | None = None
    email: str
    connected: bool = True
    provider: str = "yahoo"
    message: str | None = None


def _enforce_enter_rate_limit(key: str) -> None:
    now = time.time()
    stamps = [
        stamp
        for stamp in _enter_attempts.get(key, [])
        if now - stamp < _ENTER_WINDOW_SECONDS
    ]
    if len(stamps) >= _ENTER_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail={
                "status": "rate_limited",
                "message": (
                    "Demasiados intentos seguidos. Espera unos minutos "
                    "e inténtalo de nuevo."
                ),
            },
        )
    stamps.append(now)
    _enter_attempts[key] = stamps


def _verify_yahoo_or_http(address: str, app_password: str) -> tuple[str, str]:
    address = normalize_yahoo_address(address)
    app_password = normalize_yahoo_app_password(app_password)

    if "@" not in address:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "invalid_email",
                "message": "Indica un correo de Yahoo válido.",
            },
        )

    try:
        verify_yahoo_login(address, app_password)
    except YahooImapError as error:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "yahoo_auth_failed",
                "message": str(error),
            },
        ) from error

    return address, app_password


def persist_yahoo_mailbox(
    *,
    user_id: str,
    workspace_id: str,
    address: str,
    app_password: str,
) -> GoogleConnectionStatus:
    """Guarda el buzón Yahoo cifrado en el workspace indicado."""
    try:
        try:
            oauth_storage.client.table("communication_accounts").update(
                {"status": "inactive"}
            ).eq("workspace_id", workspace_id).eq(
                "status", "active"
            ).neq("provider", "yahoo").execute()
        except Exception:
            pass

        account = oauth_storage.upsert_communication_account(
            provider="yahoo",
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
            expires_at=None,
            token_uri=None,
            scopes=["imap.mail.yahoo.com"],
            metadata={
                "protocol": "imap",
                "host": "imap.mail.yahoo.com",
                "connected_by_profile_id": user_id,
                "workspace_id": workspace_id,
            },
        )
    except (OAuthStorageError, OAuthCredentialError) as error:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "Yahoo autenticó, pero no se pudo guardar la conexión.",
                "technical_detail": str(error),
            },
        ) from error

    return GoogleConnectionStatus(
        connected=True,
        email=address,
        provider="yahoo",
        has_access_token=True,
        has_refresh_token=False,
        scopes=["imap.mail.yahoo.com"],
        message=(
            "Buzón Yahoo conectado. Siguiente paso: descargar y clasificar "
            "los últimos seis meses."
        ),
        login_url=None,
    )


@router.post("/enter", response_model=YahooEnterResponse)
def yahoo_enter(
    payload: YahooConnectRequest,
    request: Request,
) -> YahooEnterResponse:
    """Correo + clave de Yahoo = sesión. El usuario no da de alta Donexto."""
    client_host = request.client.host if request.client else "unknown"
    address_key = normalize_yahoo_address(payload.email)
    _enforce_enter_rate_limit(f"{client_host}:{address_key}")

    address, app_password = _verify_yahoo_or_http(
        payload.email,
        payload.app_password,
    )
    session = mint_yahoo_session_or_http(address)
    persist_yahoo_mailbox(
        user_id=session["user_id"],
        workspace_id=session["workspace_id"],
        address=address,
        app_password=app_password,
    )
    expires_raw = session.get("expires_in")
    expires_in = int(expires_raw) if expires_raw else None
    return YahooEnterResponse(
        access_token=session["access_token"],
        refresh_token=session["refresh_token"],
        expires_in=expires_in,
        email=address,
        connected=True,
        provider="yahoo",
        message="Entraste con Yahoo. El buzón ya quedó conectado.",
    )


@router.post("/connect")
def yahoo_connect(payload: YahooConnectRequest) -> GoogleConnectionStatus:
    """Vincula un buzón Yahoo al workspace Donexto actual (ya logueado)."""
    context = require_request_context()
    address, app_password = _verify_yahoo_or_http(
        payload.email,
        payload.app_password,
    )

    account_email = (context.user.email or "").strip().lower()
    if account_email and address != account_email:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "mailbox_mismatch",
                "message": (
                    "El buzón Yahoo debe ser el mismo correo con el que "
                    f"entraste ({account_email})."
                ),
            },
        )

    return persist_yahoo_mailbox(
        user_id=context.user.id,
        workspace_id=context.workspace_id,
        address=address,
        app_password=app_password,
    )


@router.get("/status", response_model=GoogleConnectionStatus)
def yahoo_status() -> GoogleConnectionStatus:
    """Estado del buzón Yahoo activo del workspace (si existe)."""
    context = require_request_context()
    account = context.google_account
    if not account or str(account.get("provider") or "") not in (
        "yahoo",
        "imap",
    ):
        return GoogleConnectionStatus(
            connected=False,
            provider="yahoo",
            message="No hay buzón Yahoo activo en este espacio.",
            login_url=None,
        )

    credentials = oauth_storage.get_credentials(str(account["id"]))
    return GoogleConnectionStatus(
        connected=bool(credentials and credentials.get("access_token")),
        email=account.get("email"),
        provider="yahoo",
        has_access_token=bool(
            credentials and credentials.get("access_token")
        ),
        has_refresh_token=False,
        scopes=(credentials or {}).get("scopes", []),
        message="Buzón Yahoo conectado.",
    )


@router.post("/disconnect", response_model=GoogleConnectionStatus)
def yahoo_disconnect() -> GoogleConnectionStatus:
    context = require_request_context()
    account = context.google_account
    if not account or str(account.get("provider") or "") not in (
        "yahoo",
        "imap",
    ):
        return GoogleConnectionStatus(
            connected=False,
            provider="yahoo",
            message="No había buzón Yahoo que desconectar.",
        )

    oauth_storage.disconnect_account(str(account["id"]))
    return GoogleConnectionStatus(
        connected=False,
        provider="yahoo",
        message="Buzón Yahoo desconectado.",
    )
