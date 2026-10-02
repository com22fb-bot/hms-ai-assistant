"""Yahoo Mail: OAuth (mail-r pendiente) y IMAP con contraseña de app.

La contraseña de app es la ruta que lee el buzón ahora. El OAuth se
queda para cuando Yahoo entregue mail-r. No activar
YAHOO_MAIL_READ_ENABLED. La contraseña de app se cifra y no se registra.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import escape
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field

from app.core.config import settings
from app.schemas.gmail import GoogleConnectionStatus
from app.services.oauth_storage import (
    OAuthCredentialError,
    OAuthStateError,
    OAuthStorageError,
    oauth_storage,
)
from app.security.identity import (
    authenticate_request,
    require_request_context,
    resolve_workspace_context,
)
from app.security.rate_limit import allow_request
from app.services.imap_provider import YAHOO_IMAP
from app.services.yahoo_imap import (
    YahooImapError,
    normalize_yahoo_app_password,
    stored_yahoo_uses_app_password,
    verify_yahoo_app_login,
)
from app.services.yahoo_oauth import (
    YahooOAuthError,
    build_yahoo_authorization_url,
    encode_login_hint_in_state_prefix,
    exchange_yahoo_code,
    fetch_yahoo_userinfo,
    granted_mail_read,
    login_hint_from_oauth_state,
    normalize_yahoo_intent,
    oauth_identity_block_message,
    require_continuar_login_hint,
    require_yahoo_oauth_config,
    sanitize_return_to,
    yahoo_email_from_userinfo,
    yahoo_intent_from_state,
)
from app.services.yahoo_session import auth_user_exists, mint_yahoo_session_or_http


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
    intent: str | None = None
    login_hint: str | None = None


def _signup_redirect(return_to: str, email: str) -> RedirectResponse:
    """Yahoo identificó el correo, pero no hay cuenta Donexto: no hay sesión."""
    query = urlencode(
        {
            "donexto": "signup",
            "reason": "no_account",
            "email": email,
        }
    )
    return RedirectResponse(
        url=f"{return_to.rstrip('/')}?{query}",
        status_code=302,
    )


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
            status="active",
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
                "mail_read": mail_read,
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
            login_url=None,
            mail_read_available=settings.yahoo_mail_read_enabled,
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
    intent = normalize_yahoo_intent(payload.intent if payload else None)
    hint = require_continuar_login_hint(
        payload.login_hint if payload else None
    )
    if intent == "login" and hint and not auth_user_exists(hint):
        raise HTTPException(
            status_code=403,
            detail={
                "status": "no_donexto_account",
                "message": (
                    "Ese correo no tiene cuenta Donexto. "
                    "Pulsa Suscribirse."
                ),
            },
        )
    return_to = sanitize_return_to(
        (payload.return_to if payload else None)
        or request.headers.get("origin")
    )
    try:
        state = oauth_storage.create_oauth_state(
            provider="yahoo",
            ttl_minutes=15,
            return_to=return_to,
            state_prefix=encode_login_hint_in_state_prefix(intent, hint),
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
        "intent": intent,
        "authorization_url": build_yahoo_authorization_url(
            state,
            login_hint=hint,
        ),
    }


def _yahoo_callback_error_message(error: str, description: str) -> str:
    code = (error or "").lower().replace("-", "_")
    text = (description or "").lower().replace("+", " ")
    if code == "invalid_scope" or "invalid scope" in text:
        return (
            "Yahoo no autorizó leer este buzón. "
            "Vuelve a Donexto: no hace falta firmar otra vez. "
            "Falta el permiso de correo de la app."
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

    return_to = sanitize_return_to(str(state_context.get("return_to") or ""))
    expected_hint = login_hint_from_oauth_state(state)
    mismatch = oauth_identity_block_message(
        expected_hint,
        address,
        provider_label="Yahoo",
    )
    if mismatch:
        query = urlencode(
            {
                "donexto": "oauth_error",
                "reason": mismatch[:280],
            }
        )
        return RedirectResponse(
            url=f"{return_to.rstrip('/')}?{query}",
            status_code=302,
        )

    intent = yahoo_intent_from_state(state)
    exists = auth_user_exists(address)
    if intent != "signup" and not exists:
        return _signup_redirect(return_to, address)

    session = mint_yahoo_session_or_http(
        address,
        allow_create=intent == "signup",
    )
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

    fragment = urlencode(
        {
            "access_token": session["access_token"],
            "refresh_token": session["refresh_token"],
            "token_type": "bearer",
            "expires_in": session.get("expires_in") or "3600",
            "type": "magiclink",
            "is_new": str(session.get("is_new") is True).lower(),
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
    scopes = list((credentials or {}).get("scopes") or [])
    has_token = bool(credentials and credentials.get("access_token"))
    if stored_yahoo_uses_app_password(credentials):
        return GoogleConnectionStatus(
            connected=has_token,
            email=account.get("email"),
            provider="yahoo",
            has_access_token=has_token,
            has_refresh_token=False,
            scopes=scopes,
            message=(
                "Buzón Yahoo conectado en solo lectura con contraseña de app."
                if has_token
                else "Falta volver a conectar Yahoo."
            ),
            login_url=None,
            mail_read_available=has_token,
        )
    mail_read = granted_mail_read({"scope": " ".join(scopes)})
    return GoogleConnectionStatus(
        connected=bool(has_token and mail_read),
        email=account.get("email"),
        provider="yahoo",
        has_access_token=has_token,
        has_refresh_token=False,
        scopes=scopes,
        message=(
            "Buzón Yahoo autorizado."
            if mail_read
            else (
                "Entraste con Yahoo. Falta el permiso de lectura del "
                "correo (mail-r); sin eso Donexto no puede abrir el buzón."
            )
        ),
        login_url=None,
        mail_read_available=settings.yahoo_mail_read_enabled,
    )


_YAHOO_IMAP_SIGNUP = "yahoo_imap"


def _yahoo_session_if_present(request: Request):
    authorization = request.headers.get("authorization", "").strip()
    if not authorization:
        return None
    user = authenticate_request(request)
    if not user.donexto_verified:
        raise HTTPException(
            status_code=403,
            detail={
                "status": "donexto_unverified",
                "message": "Confirma tu correo Donexto antes de conectar Yahoo.",
            },
        )
    return resolve_workspace_context(request, user)


def persist_yahoo_app_mailbox(
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
            "provider", "yahoo"
        ).execute()
    except Exception:
        pass

    try:
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
            token_uri=f"imap://{YAHOO_IMAP.host}:{YAHOO_IMAP.port}",
            scopes=["imap", "readonly"],
            metadata={
                "protocol": "imap",
                "auth": "app_password",
                "host": YAHOO_IMAP.host,
                "port": YAHOO_IMAP.port,
                "readonly": True,
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
            },
        ) from error


class YahooImapConnectResponse(BaseModel):
    connected: bool = True
    email: str
    provider: str = "yahoo"
    message: str
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str | None = None
    expires_in: int | None = None


@router.post("/imap/connect", response_model=YahooImapConnectResponse)
def yahoo_imap_connect(
    payload: YahooConnectRequest,
    request: Request,
) -> YahooImapConnectResponse:
    """LOGIN IMAP real con contraseña de app. No usa YAHOO_MAIL_READ_ENABLED."""
    client_host = getattr(getattr(request, "client", None), "host", None) or "unknown"
    if not allow_request(f"yahoo-imap:{client_host}", max_requests=8, window_seconds=60):
        raise HTTPException(
            status_code=429,
            detail={
                "status": "rate_limited",
                "code": "rate_limited",
                "message": "Demasiados intentos seguidos. Espera un momento.",
            },
        )

    context = _yahoo_session_if_present(request)
    try:
        verified = verify_yahoo_app_login(payload.email, payload.app_password)
    except YahooImapError as error:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "yahoo_auth_failed",
                "code": error.code,
                "message": str(error),
            },
        ) from error

    if context is not None and verified != context.user.email.strip().lower():
        raise HTTPException(
            status_code=403,
            detail={
                "status": "email_mismatch",
                "code": "email_mismatch",
                "message": (
                    "Donexto solo lee el correo de esta cuenta. "
                    "Usa el mismo Yahoo con el que entraste."
                ),
            },
        )

    access_token = None
    refresh_token = None
    expires_in = None
    if context is None:
        session = mint_yahoo_session_or_http(
            verified,
            allow_create=True,
            signup_via=_YAHOO_IMAP_SIGNUP,
            provider_label="Yahoo",
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

    persist_yahoo_app_mailbox(
        user_id=user_id,
        workspace_id=workspace_id,
        address=verified,
        app_password=normalize_yahoo_app_password(payload.app_password),
    )
    return YahooImapConnectResponse(
        connected=True,
        email=verified,
        message=(
            "Yahoo conectado en solo lectura con contraseña de app. "
            "Donexto no marca tus correos como leídos. Puedes revocar "
            "esa contraseña en Yahoo cuando quieras."
        ),
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer" if access_token else None,
        expires_in=expires_in,
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

    oauth_storage.disconnect_account(str(account["id"]), delete_credentials=True)
    return GoogleConnectionStatus(
        connected=False,
        provider="yahoo",
        message="Buzón Yahoo desconectado.",
    )
