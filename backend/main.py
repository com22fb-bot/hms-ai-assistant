from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.api.ai import router as ai_router
from app.api.auth import (
    get_active_google_credentials,
    get_connected_google_email,
    get_google_connection_status,
    router as auth_router,
)
from app.api.gmail import create_gmail_router
from app.api.system import router as system_router
from app.core.config import settings


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
    allow_origins=settings.frontend_origins,
    allow_origin_regex=(
        r"https://.*\."
        r"(app\.github\.dev|githubpreview\.dev|vercel\.app)"
    ),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
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
    connection = get_google_connection_status()

    connection_status = (
        "Conectada"
        if connection.connected
        else "No conectada"
    )

    account_email = get_connected_google_email()

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
# REGISTRO DE ROUTERS
# ============================================================

gmail_router = create_gmail_router(
    get_active_google_credentials,
)

app.include_router(system_router)
app.include_router(ai_router)
app.include_router(auth_router)
app.include_router(gmail_router)