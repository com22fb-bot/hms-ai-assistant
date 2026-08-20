"""Conexión de Yahoo Mail (IMAP con correo y clave de Yahoo)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
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


router = APIRouter(prefix="/auth/yahoo", tags=["Yahoo Mail"])


class YahooConnectRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    app_password: str = Field(min_length=6, max_length=256)


@router.post("/connect")
def yahoo_connect(payload: YahooConnectRequest) -> GoogleConnectionStatus:
    """Vincula un buzón Yahoo al workspace Donexto actual."""
    context = require_request_context()
    address = normalize_yahoo_address(payload.email)
    app_password = normalize_yahoo_app_password(payload.app_password)

    if "@" not in address:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "invalid_email",
                "message": "Indica un correo de Yahoo válido.",
            },
        )

    account_email = (context.user.email or "").strip().lower()
    if account_email and address != account_email:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "mailbox_mismatch",
                "message": (
                    "El buzón Yahoo debe ser el mismo correo de tu cuenta "
                    f"Donexto ({account_email})."
                ),
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

    try:
        # Desactiva otros buzones del workspace para que Yahoo quede como activo.
        try:
            oauth_storage.client.table("communication_accounts").update(
                {"status": "inactive"}
            ).eq("workspace_id", context.workspace_id).eq(
                "status", "active"
            ).neq("provider", "yahoo").execute()
        except Exception:
            pass

        account = oauth_storage.upsert_communication_account(
            provider="yahoo",
            provider_account_id=address,
            email=address,
            display_name=address,
            workspace_id=context.workspace_id,
            connected_by_profile_id=context.user.id,
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
                "connected_by_profile_id": context.user.id,
                "workspace_id": context.workspace_id,
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
        message="Buzón Yahoo conectado. Siguiente paso: descargar y clasificar los últimos seis meses.",
        login_url=None,
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
