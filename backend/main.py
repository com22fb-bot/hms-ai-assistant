from __future__ import annotations

import secrets
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from app.api.system import router as system_router
from app.core.config import settings
from app.schemas.gmail import (
    GmailMessagesResponse,
    GoogleConnectionStatus,
)
from app.services.gmail import create_credentials, list_messages


# ============================================================
# CONFIGURACIÓN
# ============================================================

SUPABASE_URL = settings.supabase_url
SUPABASE_SECRET_KEY = settings.supabase_secret_key

GOOGLE_CLIENT_ID = settings.google_client_id
GOOGLE_CLIENT_SECRET = settings.google_client_secret
GOOGLE_REDIRECT_URI = settings.google_redirect_uri

FRONTEND_ORIGINS = settings.frontend_origins
GOOGLE_SCOPES = settings.google_scopes


# ============================================================
# APLICACIÓN FASTAPI
# ============================================================

app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_origin_regex=(
        r"https://.*\."
        r"(app\.github\.dev|githubpreview\.dev|vercel\.app)"
    ),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)



# ============================================================
# ALMACENAMIENTO TEMPORAL
# ============================================================

# En esta versión los datos permanecen en memoria.
# Cuando FastAPI se reinicia, será necesario reconectar Gmail.
#
# En una etapa posterior los tokens se guardarán cifrados
# y asociados a una cuenta en Supabase.

oauth_states: dict[str, bool] = {}
google_credentials: dict[str, Any] = {}
google_account: dict[str, Any] = {}


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def validate_google_environment() -> None:
    """Verifica las variables necesarias para Google OAuth."""
    missing_variables: list[str] = []

    if not GOOGLE_CLIENT_ID:
        missing_variables.append("GOOGLE_CLIENT_ID")

    if not GOOGLE_CLIENT_SECRET:
        missing_variables.append("GOOGLE_CLIENT_SECRET")

    if not GOOGLE_REDIRECT_URI:
        missing_variables.append("GOOGLE_REDIRECT_URI")

    if missing_variables:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": (
                    "Faltan variables de Google OAuth "
                    "en el entorno."
                ),
                "missing_variables": missing_variables,
            },
        )


def create_google_flow(
    state: str | None = None,
) -> Flow:
    """Construye el flujo OAuth de Google."""
    validate_google_environment()

    client_config = {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": (
                "https://accounts.google.com/o/oauth2/auth"
            ),
            "token_uri": (
                "https://oauth2.googleapis.com/token"
            ),
            "redirect_uris": [GOOGLE_REDIRECT_URI],
        }
    }

    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=GOOGLE_SCOPES,
        state=state,
        autogenerate_code_verifier=False,
    )

    flow.redirect_uri = GOOGLE_REDIRECT_URI

    return flow


def get_active_google_credentials() -> Credentials:
    """Obtiene credenciales válidas de la cuenta conectada."""
    validate_google_environment()

    return create_credentials(
        stored_credentials=google_credentials,
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
    )


# ============================================================
# RUTAS GENERALES
# ============================================================

@app.get("/")
def root() -> dict[str, str]:
    return {
        "status": "ok",
        "application": settings.app_name,
        "version": settings.app_version,
        "documentation": "/docs",
        "dashboard": "/dashboard",
        "google_login": "/auth/google/login",
        "google_status": "/auth/google/status",
        "gmail_messages": "/gmail/messages",
    }


@app.get(
    "/dashboard",
    response_class=HTMLResponse,
)
def dashboard() -> str:
    connection_status = (
        "Conectada"
        if google_credentials
        else "No conectada"
    )

    account_email = google_account.get(
        "email",
        "Sin cuenta identificada",
    )

    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
        >
        <title>HMS AI Assistant</title>

        <style>
            body {{
                margin: 0;
                padding: 40px 20px;
                background: #f4f7fb;
                color: #1f2937;
                font-family: Arial, sans-serif;
            }}

            .container {{
                max-width: 760px;
                margin: 0 auto;
                padding: 32px;
                background: white;
                border-radius: 16px;
                box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08);
            }}

            h1 {{
                margin-top: 0;
                color: #174ea6;
            }}

            .status {{
                padding: 14px;
                margin: 20px 0;
                background: #eef4ff;
                border-radius: 10px;
            }}

            .account {{
                margin-top: 8px;
                color: #4b5563;
                font-size: 14px;
            }}

            a.button {{
                display: inline-block;
                padding: 12px 18px;
                margin: 6px 6px 6px 0;
                color: white;
                background: #174ea6;
                border-radius: 8px;
                text-decoration: none;
            }}

            a.secondary {{
                background: #374151;
            }}
        </style>
    </head>

    <body>
        <main class="container">
            <h1>HMS AI Assistant</h1>

            <p>
                Backend de administración y conexión
                de cuentas de correo.
            </p>

            <div class="status">
                <strong>Google Gmail:</strong>
                {connection_status}

                <div class="account">
                    {account_email}
                </div>
            </div>

            <a
                class="button"
                href="/auth/google/login"
            >
                Conectar cuenta de Google
            </a>

            <a
                class="button secondary"
                href="/auth/google/status"
            >
                Consultar estado
            </a>

            <a
                class="button secondary"
                href="/gmail/messages"
            >
                Consultar correos
            </a>

            <a
                class="button secondary"
                href="/database-health"
            >
                Probar Supabase
            </a>

            <a
                class="button secondary"
                href="/docs"
            >
                Documentación API
            </a>
        </main>
    </body>
    </html>
    """


# ============================================================
# AUTENTICACIÓN DE GOOGLE
# ============================================================

@app.get("/auth/google/login")
def google_login() -> RedirectResponse:
    flow = create_google_flow()

    state = secrets.token_urlsafe(32)
    oauth_states[state] = True

    authorization_url, returned_state = (
        flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state=state,
        )
    )

    if returned_state != state:
        oauth_states.pop(state, None)

        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": (
                    "No fue posible crear "
                    "un estado OAuth válido."
                ),
            },
        )

    return RedirectResponse(
        url=authorization_url,
        status_code=302,
    )


@app.get("/auth/google/callback")
def google_callback(
    request: Request,
) -> HTMLResponse:
    oauth_error = request.query_params.get("error")

    if oauth_error:
        error_description = request.query_params.get(
            "error_description",
            "Google rechazó la autorización.",
        )

        return HTMLResponse(
            status_code=400,
            content=f"""
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <meta
                    name="viewport"
                    content="width=device-width, initial-scale=1.0"
                >
                <title>Error de conexión</title>
            </head>

            <body>
                <h1>No fue posible conectar Google</h1>
                <p>{error_description}</p>
                <p>
                    <a href="/auth/google/login">
                        Intentar nuevamente
                    </a>
                </p>
            </body>
            </html>
            """,
        )

    state = request.query_params.get("state")

    if not state or state not in oauth_states:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "message": (
                    "El estado OAuth es inválido "
                    "o expiró."
                ),
            },
        )

    flow = create_google_flow(state=state)

    try:
        flow.fetch_token(
            authorization_response=str(request.url)
        )

    except Exception as error:
        oauth_states.pop(state, None)

        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "message": (
                    "No fue posible obtener "
                    "el token de Google."
                ),
                "technical_detail": str(error),
            },
        ) from error

    oauth_states.pop(state, None)

    credentials: Credentials = flow.credentials

    google_credentials.clear()

    google_credentials.update(
        {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "scopes": list(credentials.scopes or []),
            "expiry": (
                credentials.expiry.isoformat()
                if credentials.expiry
                else None
            ),
            "connected": True,
        }
    )

    google_account.clear()

    try:
        from googleapiclient.discovery import build

        oauth_service = build(
            "oauth2",
            "v2",
            credentials=credentials,
            cache_discovery=False,
        )

        account_information = (
            oauth_service.userinfo()
            .get()
            .execute()
        )

        google_account.update(
            {
                "email": account_information.get(
                    "email",
                    "",
                ),
                "name": account_information.get(
                    "name",
                    "",
                ),
                "picture": account_information.get(
                    "picture",
                    "",
                ),
            }
        )

    except Exception:
        # La conexión de Gmail continúa siendo válida aunque
        # no sea posible recuperar los datos del perfil.
        google_account.clear()

    connected_email = google_account.get(
        "email",
        "Cuenta conectada",
    )

    return HTMLResponse(
        status_code=200,
        content=f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta
                name="viewport"
                content="width=device-width, initial-scale=1.0"
            >
            <title>Google conectado</title>

            <style>
                body {{
                    margin: 0;
                    padding: 40px 20px;
                    background: #f4f7fb;
                    color: #1f2937;
                    font-family: Arial, sans-serif;
                }}

                main {{
                    max-width: 640px;
                    margin: 0 auto;
                    padding: 32px;
                    background: white;
                    border-radius: 16px;
                    box-shadow:
                        0 8px 30px rgba(0, 0, 0, 0.08);
                }}

                h1 {{
                    color: #137333;
                }}

                a {{
                    display: inline-block;
                    margin-top: 16px;
                    padding: 12px 18px;
                    color: white;
                    background: #174ea6;
                    border-radius: 8px;
                    text-decoration: none;
                }}
            </style>
        </head>

        <body>
            <main>
                <h1>Cuenta de Google conectada</h1>

                <p>
                    La autorización se completó correctamente.
                </p>

                <p>
                    <strong>Cuenta:</strong>
                    {connected_email}
                </p>

                <a href="/dashboard">
                    Regresar al panel
                </a>
            </main>
        </body>
        </html>
        """,
    )


@app.get(
    "/auth/google/status",
    response_model=GoogleConnectionStatus,
)
def google_status() -> GoogleConnectionStatus:
    if not google_credentials:
        return GoogleConnectionStatus(
            connected=False,
            message=(
                "No hay una cuenta de Google conectada."
            ),
            login_url="/auth/google/login",
        )

    return GoogleConnectionStatus(
        connected=True,
        email=google_account.get("email") or None,
        has_access_token=bool(
            google_credentials.get("token")
        ),
        has_refresh_token=bool(
            google_credentials.get("refresh_token")
        ),
        scopes=google_credentials.get(
            "scopes",
            [],
        ),
        message="Cuenta de Google conectada.",
    )


@app.post(
    "/auth/google/disconnect",
    response_model=GoogleConnectionStatus,
)
def google_disconnect() -> GoogleConnectionStatus:
    google_credentials.clear()
    google_account.clear()
    oauth_states.clear()

    return GoogleConnectionStatus(
        connected=False,
        message="Cuenta de Google desconectada.",
        login_url="/auth/google/login",
    )


# ============================================================
# GMAIL
# ============================================================

@app.get(
    "/gmail/messages",
    response_model=GmailMessagesResponse,
)
def gmail_messages(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description=(
            "Cantidad máxima de correos que se consultarán."
        ),
    ),
    query: str | None = Query(
        default=None,
        description=(
            "Consulta opcional utilizando la sintaxis "
            "de búsqueda de Gmail."
        ),
    ),
) -> GmailMessagesResponse:
    credentials = get_active_google_credentials()

    messages = list_messages(
        credentials=credentials,
        max_results=limit,
        query=query,
    )

    return GmailMessagesResponse(
        total=len(messages),
        messages=messages,
    )


# ============================================================
# REGISTRO DE ROUTERS
# ============================================================

app.include_router(system_router)
