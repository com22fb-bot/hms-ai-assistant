from __future__ import annotations

from html import escape
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.core.config import settings
from app.schemas.gmail import GoogleConnectionStatus
from app.services.gmail import create_credentials
from app.services.oauth_storage import (
    OAuthCredentialError,
    OAuthStateError,
    OAuthStorageError,
    oauth_storage,
)

router = APIRouter(prefix="/auth/google", tags=["Google OAuth"])

GOOGLE_PROVIDER = "google"
DEFAULT_TOKEN_URI = "https://oauth2.googleapis.com/token"


def validate_google_environment() -> None:
    """Verifica las variables necesarias para Google OAuth."""
    missing_variables: list[str] = []

    if not settings.google_client_id:
        missing_variables.append("GOOGLE_CLIENT_ID")
    if not settings.google_client_secret:
        missing_variables.append("GOOGLE_CLIENT_SECRET")
    if not settings.google_redirect_uri:
        missing_variables.append("GOOGLE_REDIRECT_URI")

    if missing_variables:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "Faltan variables de Google OAuth en el entorno.",
                "missing_variables": missing_variables,
            },
        )


def create_google_flow(state: str | None = None) -> Flow:
    """Construye el flujo OAuth de Google."""
    validate_google_environment()

    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": DEFAULT_TOKEN_URI,
            "redirect_uris": [settings.google_redirect_uri],
        }
    }

    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=settings.google_scopes,
        state=state,
        autogenerate_code_verifier=False,
    )
    flow.redirect_uri = settings.google_redirect_uri
    return flow


def _load_active_google_connection() -> dict[str, Any] | None:
    """Recupera la cuenta Google activa y sus credenciales."""
    try:
        return oauth_storage.get_active_credentials(provider=GOOGLE_PROVIDER)
    except OAuthStorageError as error:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "No fue posible consultar la conexión de Google en Supabase.",
                "technical_detail": str(error),
            },
        ) from error


def _to_gmail_stored_credentials(
    stored_credentials: dict[str, Any],
) -> dict[str, Any]:
    """Adapta las credenciales persistentes al servicio Gmail."""
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


def get_active_google_credentials() -> Credentials:
    """Obtiene credenciales válidas y persiste cualquier renovación."""
    validate_google_environment()
    connection = _load_active_google_connection()

    if not connection:
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "connected": False,
                "message": "No hay una cuenta de Google conectada.",
                "login_url": "/auth/google/login",
            },
        )

    account = connection["account"]
    persistent_credentials = connection["credentials"]
    gmail_credentials = _to_gmail_stored_credentials(persistent_credentials)

    def persist_refreshed_credentials(
        refreshed_credentials: Credentials,
    ) -> None:
        oauth_storage.save_credentials(
            account_id=account["id"],
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


def get_google_connection_status() -> GoogleConnectionStatus:
    """Devuelve el estado persistente de la conexión Google."""
    connection = _load_active_google_connection()

    if not connection:
        return GoogleConnectionStatus(
            connected=False,
            message="No hay una cuenta de Google conectada.",
            login_url="/auth/google/login",
        )

    account = connection["account"]
    credentials = connection["credentials"]

    return GoogleConnectionStatus(
        connected=True,
        email=account.get("email") or None,
        has_access_token=bool(credentials.get("access_token")),
        has_refresh_token=bool(credentials.get("refresh_token")),
        scopes=credentials.get("scopes", []),
        message="Cuenta de Google conectada.",
    )


def get_connected_google_email() -> str:
    """Devuelve el correo Google conectado."""
    connection = _load_active_google_connection()
    if not connection:
        return "Sin cuenta identificada"
    return connection["account"].get("email") or "Sin cuenta identificada"


@router.get("/login")
def google_login() -> RedirectResponse:
    """Inicia el flujo de autorización de Google."""
    try:
        state = oauth_storage.create_oauth_state(
            provider=GOOGLE_PROVIDER,
            ttl_minutes=10,
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
    authorization_url, returned_state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="select_account consent",
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

    return RedirectResponse(url=authorization_url, status_code=302)


@router.get("/callback")
def google_callback(request: Request) -> HTMLResponse:
    """Procesa la autorización y persiste la cuenta en Supabase."""
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
            <p><a href="/auth/google/login">Intentar nuevamente</a></p>
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
        oauth_storage.consume_oauth_state(state, GOOGLE_PROVIDER)
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

    flow = create_google_flow(state=state)

    try:
        flow.fetch_token(authorization_response=str(request.url))
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
                "message": "Google autorizó la cuenta, pero no fue posible consultar su identidad.",
                "technical_detail": str(error),
            },
        ) from error

    account_email = (account_information.get("email") or "").strip()
    provider_account_id = str(
        account_information.get("id") or account_email
    ).strip()

    if not provider_account_id:
        raise HTTPException(
            status_code=502,
            detail={
                "status": "error",
                "message": "Google no devolvió un identificador válido para la cuenta.",
            },
        )

    if not credentials.token:
        raise HTTPException(
            status_code=502,
            detail={
                "status": "error",
                "message": "Google no devolvió un access token válido.",
            },
        )

    try:
        account = oauth_storage.upsert_communication_account(
            provider=GOOGLE_PROVIDER,
            provider_account_id=provider_account_id,
            email=account_email or None,
            display_name=account_information.get("name") or None,
            avatar_url=account_information.get("picture") or None,
            status="active",
        )
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
            },
        )
    except (OAuthCredentialError, OAuthStorageError) as error:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "Google autorizó la cuenta, pero no fue posible guardar la conexión en Supabase.",
                "technical_detail": str(error),
            },
        ) from error

    forwarded_host = request.headers.get("x-forwarded-host", "")
    forwarded_proto = request.headers.get("x-forwarded-proto", "https")

    if forwarded_host:
        frontend_host = forwarded_host.replace("-8000.", "-3000.")
        frontend_url = f"{forwarded_proto}://{frontend_host}/"
    else:
        frontend_url = next(
            (
                origin.rstrip("/") + "/"
                for origin in settings.frontend_origins
                if "localhost" not in origin and "127.0.0.1" not in origin
            ),
            "http://localhost:3000/",
        )

    return RedirectResponse(url=frontend_url, status_code=302)


@router.get("/status", response_model=GoogleConnectionStatus)
def google_status() -> GoogleConnectionStatus:
    """Consulta el estado persistente de Google."""
    return get_google_connection_status()


@router.post("/disconnect", response_model=GoogleConnectionStatus)
def google_disconnect() -> GoogleConnectionStatus:
    """Desconecta la cuenta Google activa y elimina sus tokens."""
    connection = _load_active_google_connection()

    if connection:
        try:
            oauth_storage.disconnect_account(
                account_id=connection["account"]["id"],
                delete_credentials=True,
            )
        except OAuthStorageError as error:
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "message": "No fue posible desconectar la cuenta de Google en Supabase.",
                    "technical_detail": str(error),
                },
            ) from error

    return GoogleConnectionStatus(
        connected=False,
        message="Cuenta de Google desconectada.",
        login_url="/auth/google/login",
    )
