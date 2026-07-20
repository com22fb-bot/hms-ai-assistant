import os
import secrets
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from supabase import Client, create_client


# ============================================================
# CONFIGURACIÓN
# ============================================================

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", "").strip()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "").strip()

GOOGLE_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.readonly",
]

app = FastAPI(
    title="HMS AI Assistant API",
    description="Backend de HMS AI Assistant",
    version="0.2.0",
)

# Almacenamiento temporal para esta etapa de desarrollo.
# Más adelante los tokens se guardarán cifrados en Supabase.
oauth_states: dict[str, bool] = {}
google_credentials: dict[str, Any] = {}


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def validate_google_environment() -> None:
    missing_variables = []

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
                "message": "Faltan variables de Google OAuth en el archivo .env.",
                "missing_variables": missing_variables,
            },
        )


def get_supabase_client() -> Client:
    missing_variables = []

    if not SUPABASE_URL:
        missing_variables.append("SUPABASE_URL")

    if not SUPABASE_SECRET_KEY:
        missing_variables.append("SUPABASE_SECRET_KEY")

    if missing_variables:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "Faltan variables de Supabase en el archivo .env.",
                "missing_variables": missing_variables,
            },
        )

    return create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)


def create_google_flow(state: str | None = None) -> Flow:
    validate_google_environment()

    client_config = {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
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


# ============================================================
# RUTAS GENERALES
# ============================================================

@app.get("/")
def root() -> dict[str, str]:
    return {
        "status": "ok",
        "application": "HMS AI Assistant API",
        "version": "0.2.0",
        "documentation": "/docs",
        "dashboard": "/dashboard",
        "google_login": "/auth/google/login",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "backend",
    }


@app.get("/database-health")
def database_health() -> dict[str, Any]:
    try:
        supabase = get_supabase_client()

        response = (
            supabase.table("mail_accounts")
            .select("*", count="exact")
            .limit(1)
            .execute()
        )

        record_count = response.count if response.count is not None else 0

        return {
            "status": "ok",
            "database": "connected",
            "table": "mail_accounts",
            "records": record_count,
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "database": "disconnected",
                "message": str(error),
            },
        ) from error


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> str:
    google_status = (
        "Conectada"
        if google_credentials
        else "No conectada"
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
                Backend de administración y conexión de cuentas de correo.
            </p>

            <div class="status">
                <strong>Google Gmail:</strong> {google_status}
            </div>

            <a class="button" href="/auth/google/login">
                Conectar cuenta de Google
            </a>

            <a class="button secondary" href="/auth/google/status">
                Consultar estado
            </a>

            <a class="button secondary" href="/database-health">
                Probar Supabase
            </a>

            <a class="button secondary" href="/docs">
                Documentación API
            </a>
        </main>
    </body>
    </html>
    """


# ============================================================
# GOOGLE OAUTH
# ============================================================

@app.get("/auth/google/login")
def google_login() -> RedirectResponse:
    flow = create_google_flow()

    state = secrets.token_urlsafe(32)
    oauth_states[state] = True

    authorization_url, returned_state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )

    if returned_state != state:
        raise HTTPException(
            status_code=500,
            detail="No fue posible crear un estado OAuth válido.",
        )

    return RedirectResponse(
        url=authorization_url,
        status_code=302,
    )


@app.get("/auth/google/callback")
def google_callback(request: Request) -> dict[str, Any]:
    error = request.query_params.get("error")

    if error:
        error_description = request.query_params.get(
            "error_description",
            "Google rechazó la autorización.",
        )

        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "oauth_error": error,
                "message": error_description,
            },
        )

    state = request.query_params.get("state")

    if not state or state not in oauth_states:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "message": "El estado OAuth es inválido o expiró.",
            },
        )

    flow = create_google_flow(state=state)

    try:
        flow.fetch_token(
            authorization_response=str(request.url)
        )
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "message": "No fue posible obtener el token de Google.",
                "technical_detail": str(error),
            },
        ) from error
    finally:
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
            "connected": True,
        }
    )

    return {
        "status": "ok",
        "message": "Cuenta de Google conectada correctamente.",
        "connected": True,
        "has_access_token": bool(credentials.token),
        "has_refresh_token": bool(credentials.refresh_token),
        "scopes": list(credentials.scopes or []),
        "next_step": "Consultar /auth/google/status",
    }


@app.get("/auth/google/status")
def google_status() -> dict[str, Any]:
    if not google_credentials:
        return {
            "status": "ok",
            "connected": False,
            "message": "No hay una cuenta de Google conectada.",
            "login_url": "/auth/google/login",
        }

    return {
        "status": "ok",
        "connected": True,
        "has_access_token": bool(
            google_credentials.get("token")
        ),
        "has_refresh_token": bool(
            google_credentials.get("refresh_token")
        ),
        "scopes": google_credentials.get("scopes", []),
    }
