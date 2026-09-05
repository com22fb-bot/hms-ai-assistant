"""Conexión Microsoft (Outlook, Hotmail, Microsoft 365) por OAuth."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.schemas.gmail import GoogleConnectionStatus
from app.services.oauth_storage import (
    OAuthCredentialError,
    OAuthStateError,
    OAuthStorageError,
    oauth_storage,
)
from app.services.microsoft_oauth import (
    MICROSOFT_SIGNUP_VIA,
    MicrosoftOAuthError,
    build_microsoft_authorization_url,
    exchange_microsoft_code,
    fetch_microsoft_profile,
    granted_microsoft_mail_read,
    microsoft_email_from_profile,
    microsoft_oauth_tenant,
    microsoft_tenant_from_state,
    microsoft_token_url,
    require_microsoft_oauth_config,
    sanitize_login_hint,
    sanitize_return_to,
)
from app.services.yahoo_oauth import (
    encode_login_hint_in_state_prefix,
    login_hint_from_oauth_state,
    normalize_yahoo_intent,
    oauth_email_mismatch_message,
    yahoo_intent_from_state,
)
from app.services.yahoo_session import auth_user_exists, mint_yahoo_session_or_http


router = APIRouter(prefix="/auth/microsoft", tags=["Microsoft Mail"])


class MicrosoftLoginRequest(BaseModel):
    return_to: str | None = None
    intent: str | None = None
    login_hint: str | None = None


def _signup_redirect(return_to: str, email: str) -> RedirectResponse:
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


def persist_microsoft_mailbox(
    *,
    user_id: str,
    workspace_id: str,
    address: str,
    access_token: str,
    refresh_token: str | None = None,
    expires_at: datetime | None = None,
    scopes: list[str] | None = None,
    mail_read: bool = True,
    token_uri: str | None = None,
) -> GoogleConnectionStatus:
    try:
        try:
            oauth_storage.client.table("communication_accounts").update(
                {"status": "inactive"}
            ).eq("workspace_id", workspace_id).eq(
                "status", "active"
            ).neq("provider", "microsoft").execute()
        except Exception:
            pass

        account = oauth_storage.upsert_communication_account(
            provider="microsoft",
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
            token_uri=token_uri or microsoft_token_url("common"),
            scopes=scopes or ["openid", "email", "profile", "User.Read"],
            metadata={
                "protocol": "graph",
                "auth": "oauth2",
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
                "message": "Microsoft autenticó, pero no se pudo guardar la conexión.",
                "technical_detail": str(error),
            },
        ) from error

    return GoogleConnectionStatus(
        connected=bool(mail_read),
        email=address,
        provider="microsoft",
        has_access_token=True,
        has_refresh_token=bool(refresh_token),
        scopes=scopes or [],
        message=(
            "Buzón Outlook autorizado."
            if mail_read
            else (
                "Entraste con Microsoft. Falta el permiso Mail.Read "
                "para leer el buzón."
            )
        ),
        login_url=None,
    )


def _microsoft_error_message(code: str, description: str) -> str:
    lowered = f"{code} {description}".lower()
    if "server_error" in lowered:
        return (
            "Microsoft no cerró el permiso (error interno). "
            "Vuelve a entrar con Hotmail en una ventana privada y acepta de nuevo."
        )
    if "access_denied" in lowered:
        return "No se autorizó Microsoft. Sin Aceptar, Donexto no puede entrar."
    if description.strip():
        return description.strip()[:280]
    return "Microsoft rechazó la autorización."


def _callback_error_page(
    title: str,
    message: str,
    return_to: str | None = None,
) -> HTMLResponse | RedirectResponse:
    home = sanitize_return_to(return_to) or "https://app.donexto.com/"
    query = urlencode(
        {
            "donexto": "microsoft_error",
            "reason": message[:180],
        }
    )
    return RedirectResponse(url=f"{home.rstrip('/')}?{query}", status_code=302)


@router.post("/login")
def microsoft_login(
    request: Request,
    payload: MicrosoftLoginRequest | None = None,
) -> dict[str, str]:
    require_microsoft_oauth_config()
    intent = normalize_yahoo_intent(payload.intent if payload else None)
    hint = sanitize_login_hint(payload.login_hint if payload else None)
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
    tenant = microsoft_oauth_tenant(hint)
    state_prefix = encode_login_hint_in_state_prefix(
        f"{intent}.{tenant}",
        hint,
    )
    try:
        state = oauth_storage.create_oauth_state(
            provider="microsoft",
            ttl_minutes=15,
            return_to=return_to,
            state_prefix=state_prefix,
        )
    except OAuthStorageError as error:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "No fue posible preparar el inicio de sesión de Microsoft.",
                "technical_detail": str(error),
            },
        ) from error

    return {
        "status": "ok",
        "intent": intent,
        "authorization_url": build_microsoft_authorization_url(
            state,
            login_hint=hint,
            tenant=tenant,
        ),
    }


@router.get("/callback", response_model=None)
def microsoft_callback(request: Request) -> RedirectResponse:
    oauth_error = request.query_params.get("error")
    if oauth_error:
        description = request.query_params.get("error_description") or ""
        return _callback_error_page(
            "No fue posible conectar Microsoft",
            _microsoft_error_message(oauth_error, description),
        )

    state = request.query_params.get("state")
    code = request.query_params.get("code")
    if not state or not code:
        return _callback_error_page(
            "No fue posible conectar Microsoft",
            "Microsoft no devolvió un código de autorización. Vuelve a Donexto y pulsa Continuar.",
        )

    try:
        state_context = oauth_storage.load_oauth_state(state, "microsoft")
    except OAuthStateError:
        return _callback_error_page(
            "No fue posible conectar Microsoft",
            "El inicio de sesión de Microsoft expiró o esa ventana ya se usó. "
            "Vuelve a Donexto y pulsa Continuar. No recargues la página de Microsoft.",
        )
    except OAuthStorageError:
        return _callback_error_page(
            "No fue posible conectar Microsoft",
            "No fue posible validar el inicio de sesión de Microsoft. Inténtalo de nuevo.",
        )

    return_to = sanitize_return_to(str(state_context.get("return_to") or ""))
    intent = yahoo_intent_from_state(state)
    tenant = microsoft_tenant_from_state(state)

    try:
        token_payload = exchange_microsoft_code(code, tenant=tenant)
        access = str(token_payload.get("access_token") or "")
        refresh = str(token_payload.get("refresh_token") or "") or None
        profile = fetch_microsoft_profile(access)
        address = microsoft_email_from_profile(profile)
    except MicrosoftOAuthError as error:
        return _callback_error_page(
            "No fue posible conectar Microsoft",
            str(error),
            return_to,
        )

    expected_hint = login_hint_from_oauth_state(state)
    mismatch = oauth_email_mismatch_message(
        expected_hint,
        address,
        provider_label="Microsoft",
    )
    if mismatch:
        oauth_storage.delete_oauth_state(state)
        return _callback_error_page(
            "Correo distinto al que pediste",
            mismatch,
            return_to,
        )

    oauth_storage.delete_oauth_state(state)

    exists = auth_user_exists(address)
    if intent != "signup" and not exists:
        return _signup_redirect(return_to, address)

    session = mint_yahoo_session_or_http(
        address,
        allow_create=intent == "signup",
        signup_via=MICROSOFT_SIGNUP_VIA,
        provider_label="Microsoft",
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
    persist_microsoft_mailbox(
        user_id=session["user_id"],
        workspace_id=session["workspace_id"],
        address=address,
        access_token=access,
        refresh_token=refresh,
        expires_at=expires_at,
        scopes=scopes,
        mail_read=granted_microsoft_mail_read(token_payload),
        token_uri=microsoft_token_url(tenant),
    )

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
