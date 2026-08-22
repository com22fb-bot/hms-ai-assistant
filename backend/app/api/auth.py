from __future__ import annotations

from html import escape
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from pydantic import BaseModel

from app.core.config import settings
from app.schemas.gmail import GoogleConnectionStatus
from app.security.identity import require_google_account, require_request_context
from app.security.mutation_guard import require_data_mutations_enabled
from app.services.gmail import create_credentials
from app.services.oauth_storage import (
    OAuthCredentialError,
    OAuthStateError,
    OAuthStorageError,
    oauth_storage,
)
from app.services.yahoo_oauth import granted_mail_read
from app.services.microsoft_oauth import granted_microsoft_mail_read

router = APIRouter(prefix="/auth/google", tags=["Google OAuth"])

GOOGLE_PROVIDER = "google"
DEFAULT_TOKEN_URI = "https://oauth2.googleapis.com/token"


class GoogleStartRequest(BaseModel):
    return_to: str | None = None


def _donexto_profile_email(profile_id: str) -> str:
    """Email de la cuenta Donexto (mismo buzón que debe autorizarse)."""
    if not profile_id.strip():
        return ""

    try:
        response = (
            oauth_storage.client.table("profiles")
            .select("email")
            .eq("id", profile_id)
            .limit(1)
            .execute()
        )
    except Exception:
        return ""

    rows = getattr(response, "data", None)
    if not isinstance(rows, list) or not rows:
        return ""

    return str(rows[0].get("email") or "").strip().lower()


def validate_google_environment() -> None:
    """Valida OAuth leyendo el entorno en cada llamada (no solo al import)."""
    import os

    missing_variables: list[str] = []

    if not os.getenv("GOOGLE_CLIENT_ID", "").strip():
        missing_variables.append("GOOGLE_CLIENT_ID")
    if not os.getenv("GOOGLE_CLIENT_SECRET", "").strip():
        missing_variables.append("GOOGLE_CLIENT_SECRET")
    if not os.getenv("GOOGLE_REDIRECT_URI", "").strip():
        missing_variables.append("GOOGLE_REDIRECT_URI")

    if missing_variables:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "Faltan variables de Google OAuth en el entorno del servidor (Railway Variables).",
                "missing_variables": missing_variables,
                "hint": (
                    "Deben existir en el servicio hms-ai-assistant "
                    "(no en un Shared vacío). Tras guardar: Redeploy. "
                    "Comprueba /env-status (solo true/false, sin secretos)."
                ),
            },
        )

    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "").strip().lower()
    frontend_origins = " ".join(settings.frontend_origins).lower()
    using_donexto = "donexto.com" in frontend_origins
    using_codespace_redirect = (
        "github.dev" in redirect_uri or "githubpreview.dev" in redirect_uri
    )

    if using_donexto and using_codespace_redirect:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "oauth_redirect_misconfigured",
                "message": (
                    "GOOGLE_REDIRECT_URI apunta a Codespace (github.dev). "
                    "Para Donexto en producción debe ser el callback de Railway "
                    "y la app OAuth debe llamarse Donexto en Google Cloud."
                ),
                "expected_example": (
                    "https://hms-ai-assistant-production.up.railway.app"
                    "/auth/google/callback"
                ),
                "google_console": (
                    "Pantalla OAuth: estado En producción (no Testing) "
                    "para conectar cualquier Gmail sin lista de Test users. "
                    "Nombre de app: Donexto · inicio: https://app.donexto.com"
                ),
            },
        )


def create_google_flow(state: str | None = None) -> Flow:
    import os

    validate_google_environment()

    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "").strip()

    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": DEFAULT_TOKEN_URI,
            "redirect_uris": [redirect_uri],
        }
    }

    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=settings.google_scopes,
        state=state,
        autogenerate_code_verifier=False,
    )
    flow.redirect_uri = redirect_uri
    return flow


def _is_allowed_return_url(value: str | None) -> bool:
    if not value:
        return False

    try:
        parsed = urlparse(value)
    except ValueError:
        return False

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False

    origin = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")

    if origin in {item.rstrip("/") for item in settings.frontend_origins}:
        return True

    host = (parsed.hostname or "").lower()
    return host.endswith(
        (
            ".app.github.dev",
            ".githubpreview.dev",
            ".vercel.app",
        )
    )


def _origin_from_url(value: str | None) -> str | None:
    if not value:
        return None

    try:
        parsed = urlparse(value)
    except ValueError:
        return None

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None

    candidate = f"{parsed.scheme}://{parsed.netloc}/"
    return candidate if _is_allowed_return_url(candidate) else None


def _default_frontend_url(request: Request) -> str:
    # 1) El origen real del navegador es la fuente más confiable.
    for header_name in ("origin", "referer"):
        candidate = _origin_from_url(
            request.headers.get(header_name, "").strip(),
        )
        if candidate:
            return candidate

    # 2) Si un proxy conserva el host público del frontend, úsalo tal cual.
    forwarded_host = request.headers.get("x-forwarded-host", "").strip()
    forwarded_proto = request.headers.get("x-forwarded-proto", "https").strip()

    if forwarded_host:
        candidate = _origin_from_url(
            f"{forwarded_proto}://{forwarded_host}/",
        )
        if candidate and "-8000." not in forwarded_host:
            return candidate

        # 3) Si el host corresponde al backend de Codespaces, busca un
        # frontend permitido del mismo Codespace en la configuración.
        if "-8000." in forwarded_host:
            codespace_prefix = forwarded_host.split("-8000.", 1)[0]
            configured_candidates = [
                item.rstrip("/") + "/"
                for item in settings.frontend_origins
                if item.startswith(("http://", "https://"))
            ]

            for configured in configured_candidates:
                parsed = urlparse(configured)
                configured_host = (parsed.hostname or "").lower()
                if configured_host.startswith(codespace_prefix + "-"):
                    return configured

    # 4) Preferir app.donexto.com si está configurado.
    donexto_origins = [
        item.rstrip("/") + "/"
        for item in settings.frontend_origins
        if "donexto.com" in item.lower() and item.startswith(("http://", "https://"))
    ]
    if donexto_origins:
        return donexto_origins[0]

    # 5) Último recurso: primer frontend permitido configurado.
    return next(
        (
            item.rstrip("/") + "/"
            for item in settings.frontend_origins
            if item.startswith(("http://", "https://"))
        ),
        "http://localhost:3000/",
    )


def _to_gmail_stored_credentials(
    stored_credentials: dict[str, Any],
) -> dict[str, Any]:
    expires_at = stored_credentials.get("expires_at")

    return {
        "token": stored_credentials.get("access_token"),
        "refresh_token": stored_credentials.get("refresh_token"),
        "token_uri": stored_credentials.get("token_uri") or DEFAULT_TOKEN_URI,
        "scopes": list(stored_credentials.get("scopes") or []),
        "expiry": (
            expires_at.isoformat()
            if hasattr(expires_at, "isoformat")
            else expires_at
        ),
    }


def get_google_credentials_for_account(
    account_id: str,
    *,
    expected_workspace_id: str | None = None,
) -> Credentials:
    validate_google_environment()
    account = oauth_storage.get_account(account_id)

    if not account:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "message": "La cuenta Google conectada ya no existe.",
            },
        )

    if (
        expected_workspace_id is not None
        and str(account.get("workspace_id")) != expected_workspace_id
    ):
        raise HTTPException(
            status_code=403,
            detail={
                "status": "forbidden",
                "message": "La cuenta Google pertenece a otro workspace.",
            },
        )

    persistent_credentials = oauth_storage.get_credentials(account_id)

    if not persistent_credentials:
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "connected": False,
                "message": "La conexión Google no contiene credenciales válidas.",
                "start_url": "/auth/google/start",
            },
        )

    gmail_credentials = _to_gmail_stored_credentials(persistent_credentials)

    def persist_refreshed_credentials(
        refreshed_credentials: Credentials,
    ) -> None:
        oauth_storage.save_credentials(
            account_id=account_id,
            access_token=refreshed_credentials.token,
            refresh_token=refreshed_credentials.refresh_token,
            expires_at=refreshed_credentials.expiry,
            token_uri=refreshed_credentials.token_uri or DEFAULT_TOKEN_URI,
            scopes=list(refreshed_credentials.scopes or []),
            metadata=persistent_credentials.get("metadata") or {},
        )

    return create_credentials(
        stored_credentials=gmail_credentials,
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        on_credentials_refreshed=persist_refreshed_credentials,
    )


def get_active_google_credentials() -> Credentials:
    context, account = require_google_account()
    provider = str(account.get("provider") or "google")

    if provider != "google":
        raise HTTPException(
            status_code=409,
            detail={
                "status": "google_required",
                "provider": provider,
                "message": (
                    "Esta operación requiere un buzón Gmail (Google). "
                    "El espacio tiene un buzón de otro proveedor."
                ),
                "start_url": "/auth/google/start",
            },
        )

    return get_google_credentials_for_account(
        str(account["id"]),
        expected_workspace_id=context.workspace_id,
    )


def get_google_connection_status() -> GoogleConnectionStatus:
    context = require_request_context()
    account = context.google_account

    if not account:
        return GoogleConnectionStatus(
            connected=False,
            message=(
                "Este workspace no tiene un buzón de correo conectado "
                "(Gmail, Yahoo u Outlook)."
            ),
            login_url="/auth/google/start",
        )

    credentials = oauth_storage.get_credentials(str(account["id"]))
    provider = str(account.get("provider") or "google")

    if provider in ("yahoo", "imap"):
        scopes = list((credentials or {}).get("scopes") or [])
        mail_read = granted_mail_read({"scope": " ".join(scopes)})
        has_token = bool(credentials and credentials.get("access_token"))
        return GoogleConnectionStatus(
            connected=bool(has_token and mail_read),
            email=account.get("email") or None,
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

    if provider in ("microsoft",):
        scopes = list((credentials or {}).get("scopes") or [])
        mail_read = granted_microsoft_mail_read({"scope": " ".join(scopes)})
        has_token = bool(credentials and credentials.get("access_token"))
        return GoogleConnectionStatus(
            connected=bool(has_token and mail_read),
            email=account.get("email") or None,
            provider="microsoft",
            has_access_token=has_token,
            has_refresh_token=bool(
                credentials and credentials.get("refresh_token")
            ),
            scopes=scopes,
            message=(
                "Buzón Outlook autorizado."
                if mail_read
                else (
                    "Entraste con Microsoft. Falta Mail.Read "
                    "para leer el buzón."
                )
            ),
            login_url=None,
        )

    return GoogleConnectionStatus(
        connected=bool(credentials),
        email=account.get("email") or None,
        provider="google",
        has_access_token=bool(
            credentials and credentials.get("access_token")
        ),
        has_refresh_token=bool(
            credentials and credentials.get("refresh_token")
        ),
        scopes=(credentials or {}).get("scopes", []),
        message="Cuenta de Google (Gmail) conectada a este workspace.",
    )


def get_connected_google_email() -> str:
    context = require_request_context()
    if not context.google_account:
        return "Sin cuenta identificada"
    return context.google_account.get("email") or "Sin cuenta identificada"


@router.get("/login")
def legacy_google_login() -> None:
    raise HTTPException(
        status_code=409,
        detail={
            "status": "secure_start_required",
            "message": (
                "La conexión de Google debe iniciarse desde una sesión HMS "
                "validada mediante POST /auth/google/start."
            ),
        },
    )


@router.post("/start")
def google_start(
    request: Request,
    payload: GoogleStartRequest,
) -> dict[str, str]:
    context = require_request_context()
    return_to = (
        payload.return_to.rstrip("/") + "/"
        if _is_allowed_return_url(payload.return_to)
        else _default_frontend_url(request)
    )

    try:
        state = oauth_storage.create_oauth_state(
            provider=GOOGLE_PROVIDER,
            ttl_minutes=10,
            profile_id=context.user.id,
            workspace_id=context.workspace_id,
            return_to=return_to,
        )
    except OAuthStorageError as error:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "No fue posible crear el estado OAuth en Supabase.",
                "technical_detail": str(error),
            },
        ) from error

    flow = create_google_flow(state=state)
    # login_hint + consent: el buzón debe ser el mismo Gmail de la cuenta Donexto.
    authorization_url, returned_state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        login_hint=(context.user.email or "").strip().lower(),
        state=state,
    )

    if returned_state != state:
        try:
            oauth_storage.consume_oauth_state(state, GOOGLE_PROVIDER)
        except OAuthStorageError:
            pass
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "No fue posible crear un estado OAuth válido.",
            },
        )

    return {
        "status": "ok",
        "authorization_url": authorization_url,
    }


def _public_request_url(request: Request) -> str:
    """
    URL pública del request para OAuth.

    Railway termina TLS en el proxy y a FastAPI le llega `http://...`.
    google-auth/oauthlib exige https en authorization_response.
    Preferimos reconstruir desde GOOGLE_REDIRECT_URI + query.
    """
    import os
    from urllib.parse import urlparse, urlunparse

    configured = os.getenv("GOOGLE_REDIRECT_URI", "").strip()
    if configured.startswith("https://"):
        parsed = urlparse(configured)
        query = request.url.query
        return urlunparse(
            (
                "https",
                parsed.netloc,
                parsed.path or request.url.path,
                "",
                query,
                "",
            )
        )

    # Fallback: confiar en X-Forwarded-Proto del proxy
    proto = (
        request.headers.get("x-forwarded-proto", "").split(",")[0].strip()
        or request.url.scheme
    )
    host = (
        request.headers.get("x-forwarded-host", "").split(",")[0].strip()
        or request.headers.get("host", "")
        or request.url.netloc
    )
    if proto == "http" and "localhost" not in host and "127.0.0.1" not in host:
        proto = "https"

    return str(
        request.url.replace(scheme=proto, netloc=host or request.url.netloc)
    )


@router.get("/callback", response_model=None)
def google_callback(request: Request) -> HTMLResponse | RedirectResponse:
    oauth_error = request.query_params.get("error")

    if oauth_error:
        error_description = request.query_params.get(
            "error_description",
            "Google rechazó la autorización.",
        )
        return HTMLResponse(
            status_code=400,
            content=f"""
            <!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Error de conexión</title></head><body>
            <h1>No fue posible conectar Google</h1>
            <p>{escape(error_description)}</p>
            <p>Regresa a Donexto e inténtalo nuevamente.</p>
            </body></html>
            """,
        )

    state = request.query_params.get("state")
    if not state:
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": "El estado OAuth está vacío."},
        )

    try:
        state_context = oauth_storage.consume_oauth_state(
            state,
            GOOGLE_PROVIDER,
        )
    except OAuthStateError as error:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "message": "El estado OAuth es inválido, expiró o ya fue utilizado.",
                "technical_detail": str(error),
            },
        ) from error
    except OAuthStorageError as error:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "No fue posible validar el estado OAuth en Supabase.",
                "technical_detail": str(error),
            },
        ) from error

    profile_id = str(state_context.get("profile_id") or "").strip()
    workspace_id = str(state_context.get("workspace_id") or "").strip()

    if not profile_id or not workspace_id:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "unbound_oauth_state",
                "message": (
                    "La autorización no está vinculada a una cuenta Donexto y "
                    "un workspace. Inicia la conexión nuevamente desde Donexto."
                ),
            },
        )

    flow = create_google_flow(state=state)

    try:
        flow.fetch_token(authorization_response=_public_request_url(request))
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "message": "No fue posible obtener el token de Google.",
                "technical_detail": str(error),
            },
        ) from error

    credentials: Credentials = flow.credentials

    try:
        oauth_service = build(
            "oauth2",
            "v2",
            credentials=credentials,
            cache_discovery=False,
        )
        account_information = oauth_service.userinfo().get().execute()
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail={
                "status": "error",
                "message": (
                    "Google autorizó la cuenta, pero no fue posible "
                    "consultar su identidad."
                ),
                "technical_detail": str(error),
            },
        ) from error

    account_email = (account_information.get("email") or "").strip()
    provider_account_id = str(
        account_information.get("id") or account_email
    ).strip()

    if not provider_account_id or not credentials.token:
        raise HTTPException(
            status_code=502,
            detail={
                "status": "error",
                "message": "Google no devolvió una cuenta y token válidos.",
            },
        )

    expected_email = _donexto_profile_email(profile_id)
    authorized_email = account_email.strip().lower()
    if expected_email and authorized_email and authorized_email != expected_email:
        return HTMLResponse(
            status_code=400,
            content=f"""
            <!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Gmail distinto</title></head><body>
            <h1>Debes autorizar el mismo Gmail</h1>
            <p>Tu cuenta Donexto es <strong>{escape(expected_email)}</strong>.</p>
            <p>Google autorizó <strong>{escape(authorized_email)}</strong>, que no coincide.</p>
            <p>Regresa a Donexto y autoriza la lectura de ese mismo Gmail.</p>
            </body></html>
            """,
        )

    try:
        account = oauth_storage.upsert_communication_account(
            provider=GOOGLE_PROVIDER,
            provider_account_id=provider_account_id,
            email=account_email or None,
            display_name=account_information.get("name") or None,
            avatar_url=account_information.get("picture") or None,
            workspace_id=workspace_id,
            connected_by_profile_id=profile_id,
            status="active",
        )
        # El buzón Google debe ser el mismo correo de la cuenta Donexto.
        oauth_storage.save_credentials(
            account_id=account["id"],
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            expires_at=credentials.expiry,
            token_uri=credentials.token_uri or DEFAULT_TOKEN_URI,
            scopes=list(credentials.scopes or []),
            metadata={
                "provider_account_id": provider_account_id,
                "email_verified": bool(account_information.get("verified_email")),
                "connected_by_profile_id": profile_id,
                "workspace_id": workspace_id,
            },
        )
    except (OAuthCredentialError, OAuthStorageError) as error:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": (
                    "Google autorizó la cuenta, pero no fue posible guardar "
                    "la conexión en Supabase."
                ),
                "technical_detail": str(error),
            },
        ) from error

    return_to = str(state_context.get("return_to") or "").strip()
    frontend_url = (
        return_to.rstrip("/") + "/"
        if _is_allowed_return_url(return_to)
        else _default_frontend_url(request)
    )

    return RedirectResponse(url=frontend_url, status_code=302)


@router.get("/status", response_model=GoogleConnectionStatus)
def google_status() -> GoogleConnectionStatus:
    return get_google_connection_status()


@router.post("/disconnect", response_model=GoogleConnectionStatus)
def google_disconnect() -> GoogleConnectionStatus:
    require_data_mutations_enabled("google_disconnect")
    context = require_request_context()
    account = context.google_account

    if account:
        try:
            oauth_storage.disconnect_account(
                account_id=account["id"],
                delete_credentials=True,
            )
        except OAuthStorageError as error:
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "message": "No fue posible desconectar la cuenta de Google.",
                    "technical_detail": str(error),
                },
            ) from error

    return GoogleConnectionStatus(
        connected=False,
        message="Cuenta de Google desconectada de este workspace.",
        login_url="/auth/google/start",
    )
