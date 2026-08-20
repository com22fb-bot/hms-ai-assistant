"""Conexión de Yahoo Mail por OAuth: el usuario firma en Yahoo, no da su clave."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import escape
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field

from app.schemas.gmail import GoogleConnectionStatus
from app.security.identity import require_request_context
from app.services.oauth_storage import (
    OAuthCredentialError,
    OAuthStateError,
    OAuthStorageError,
    oauth_storage,
)
from app.services.yahoo_oauth import (
    YahooOAuthError,
    build_yahoo_authorization_url,
    exchange_yahoo_code,
    fetch_yahoo_userinfo,
    granted_mail_read,
    require_yahoo_oauth_config,
    sanitize_return_to,
    yahoo_email_from_userinfo,
)
from app.services.yahoo_session import mint_yahoo_session_or_http


router = APIRouter(prefix="/auth/yahoo", tags=["Yahoo Mail"])

_PASSWORD_REJECTED = {
    "status": "yahoo_password_not_accepted",
    "message": (
        "Donexto no pide la contraseña de Yahoo ni de ningún buzón. "
        "Pulsa Continuar con Yahoo y firma en el sitio de Yahoo."
    ),
}


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


class YahooLoginRequest(BaseModel):
    return_to: str | None = None


def persist_yahoo_mailbox(
    *,
    user_id: str,
    workspace_id: str,
    address: str,
    access_token: str,
    refresh_token: str | None = None,
    expires_at: datetime | None = None,
    scopes: list[str] | None = None,
    mail_read: bool = True,
) -> GoogleConnectionStatus:
    """Guarda tokens OAuth de Yahoo cifrados. Nunca una contraseña."""
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
            status="active" if mail_read else "inactive",
        )
        oauth_storage.save_credentials(
            account_id=account["id"],
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            token_uri="https://api.login.yahoo.com/oauth2/get_token",
            scopes=scopes or ["openid", "email", "profile"],
            metadata={
                "protocol": "imap",
                "auth": "oauthbearer",
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

    if not mail_read:
        return GoogleConnectionStatus(
            connected=False,
            email=address,
            provider="yahoo",
            has_access_token=True,
            has_refresh_token=bool(refresh_token),
            scopes=scopes or [],
            message=(
                "Entraste con Yahoo. Para leer el buzón, Yahoo debe aprobar "
                "el alcance de correo (mail-r) en la app de desarrollador."
            ),
            login_url="/auth/yahoo/login",
        )

    return GoogleConnectionStatus(
        connected=True,
        email=address,
        provider="yahoo",
        has_access_token=True,
        has_refresh_token=bool(refresh_token),
        scopes=scopes or [],
        message=(
            "Buzón Yahoo autorizado. Siguiente paso: descargar y clasificar "
            "los últimos seis meses."
        ),
        login_url=None,
    )


def _reject_yahoo_password() -> None:
    raise HTTPException(status_code=410, detail=_PASSWORD_REJECTED)


@router.post("/enter", response_model=YahooEnterResponse)
def yahoo_enter(
    payload: YahooConnectRequest,
    request: Request,
) -> YahooEnterResponse:
    """Deshabilitado: Donexto no acepta la clave de Yahoo."""
    _reject_yahoo_password()
    raise AssertionError("unreachable")


@router.post("/connect")
def yahoo_connect(payload: YahooConnectRequest) -> GoogleConnectionStatus:
    """Deshabilitado: reconectar Yahoo es firmar otra vez en Yahoo."""
    _reject_yahoo_password()
    raise AssertionError("unreachable")


@router.post("/login")
def yahoo_login(
    request: Request,
    payload: YahooLoginRequest | None = None,
) -> dict[str, str]:
    """Devuelve la URL para firmar en el sitio de Yahoo."""
    require_yahoo_oauth_config()
    return_to = sanitize_return_to(
        (payload.return_to if payload else None)
        or request.headers.get("origin")
    )
    try:
        state = oauth_storage.create_oauth_state(
            provider="yahoo",
            ttl_minutes=15,
            return_to=return_to,
        )
    except OAuthStorageError as error:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "No fue posible preparar el inicio de sesión de Yahoo.",
                "technical_detail": str(error),
            },
        ) from error

    return {
        "status": "ok",
        "authorization_url": build_yahoo_authorization_url(state),
    }


def _yahoo_callback_error_message(error: str, description: str) -> str:
    code = (error or "").lower().replace("-", "_")
    text = (description or "").lower().replace("+", " ")
    if code == "invalid_scope" or "invalid scope" in text:
        return (
            "Yahoo no aceptó el permiso de correo en esta app. "
            "Por ahora Donexto solo pide identidad (openid, email, profile). "
            "La lectura del buzón (mail-r) hay que solicitarla en "
            "https://senders.yahooinc.com/developer/developer-access/"
        )
    return description or "Yahoo rechazó la autorización."


def _callback_error_page(title: str, message: str) -> HTMLResponse:
    return HTMLResponse(
        status_code=400,
        content=f"""
        <!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{escape(title)}</title></head><body>
        <h1>{escape(title)}</h1>
        <p>{escape(message)}</p>
        <p><a href="https://app.donexto.com/">Volver a Donexto</a></p>
        </body></html>
        """,
    )


@router.get("/callback", response_model=None)
def yahoo_callback(request: Request) -> HTMLResponse | RedirectResponse:
    oauth_error = request.query_params.get("error")
    if oauth_error:
        description = _yahoo_callback_error_message(
            oauth_error,
            request.query_params.get("error_description") or "",
        )
        return _callback_error_page("No fue posible conectar Yahoo", description)

    state = request.query_params.get("state")
    code = request.query_params.get("code")
    if not state or not code:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "message": "Yahoo no devolvió un código de autorización.",
            },
        )

    try:
        state_context = oauth_storage.consume_oauth_state(state, "yahoo")
    except OAuthStateError as error:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "message": "El inicio de sesión de Yahoo expiró. Inténtalo de nuevo.",
                "technical_detail": str(error),
            },
        ) from error
    except OAuthStorageError as error:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "No fue posible validar el inicio de sesión de Yahoo.",
                "technical_detail": str(error),
            },
        ) from error

    try:
        token_payload = exchange_yahoo_code(code)
        access = str(token_payload.get("access_token") or "")
        refresh = str(token_payload.get("refresh_token") or "") or None
        userinfo = fetch_yahoo_userinfo(access)
        address = yahoo_email_from_userinfo(userinfo)
    except YahooOAuthError as error:
        return _callback_error_page("No fue posible conectar Yahoo", str(error))

    session = mint_yahoo_session_or_http(address)
    expires_in = token_payload.get("expires_in")
    expires_at = None
    if expires_in:
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=int(expires_in)
            )
        except (TypeError, ValueError):
            expires_at = None

    raw_scope = str(token_payload.get("scope") or "")
    scopes = [part for part in raw_scope.replace(",", " ").split() if part]
    persist_yahoo_mailbox(
        user_id=session["user_id"],
        workspace_id=session["workspace_id"],
        address=address,
        access_token=access,
        refresh_token=refresh,
        expires_at=expires_at,
        scopes=scopes,
        mail_read=granted_mail_read(token_payload),
    )

    return_to = sanitize_return_to(str(state_context.get("return_to") or ""))
    fragment = urlencode(
        {
            "access_token": session["access_token"],
            "refresh_token": session["refresh_token"],
            "token_type": "bearer",
            "expires_in": session.get("expires_in") or "3600",
            "type": "magiclink",
        }
    )
    return RedirectResponse(
        url=f"{return_to.rstrip('/')}/#{fragment}",
        status_code=302,
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
