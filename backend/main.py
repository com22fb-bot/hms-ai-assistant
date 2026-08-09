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
from app.api.cases import router as cases_router
from app.api.gmail import create_gmail_router
from app.api.guided_import import router as guided_import_router
from app.api.identity import router as identity_router
from app.api.messages import router as messages_router
from app.api.push_notifications import router as push_router
from app.api.system import router as system_router
from app.api.sync_jobs import router as sync_jobs_router
from app.api.yahoo_mail import router as yahoo_mail_router
from app.core.config import settings
from app.middleware.authentication_context import AuthenticationContextMiddleware
from app.middleware.incident_logging import IncidentLoggingMiddleware
from app.services.gmail_sync_job_service import resume_incomplete_jobs
from app.services.automatic_mail_scheduler import start_automatic_mail_scheduler


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


app.add_middleware(AuthenticationContextMiddleware)
app.add_middleware(IncidentLoggingMiddleware)


@app.on_event("startup")
def resume_durable_gmail_sync_jobs() -> None:
    """Recupera trabajos solo cuando las mutaciones están habilitadas."""
    if settings.data_mutations_enabled:
        resume_incomplete_jobs()




@app.on_event("startup")
def start_hms_automatic_mail_sync() -> None:
    start_automatic_mail_scheduler()


@app.get("/")
def root() -> dict[str, str]:
    import os

    return {
        "status": "ok",
        "application": settings.app_name,
        "version": settings.app_version,
        "deploy_marker": os.getenv(
            "HMS_DEPLOY_MARKER",
            "donexto-api-0.4.3",
        ),
        "documentation": "/docs",
        "dashboard": "/cases/dashboard",
        "google_login": "/auth/google/login",
        "google_status": "/auth/google/status",
        "gmail_messages": "/gmail/messages",
        "stored_messages": "/messages/stored",
        "cases": "/cases",
        "case_processing": "/cases/process",
    }


@app.get(
    "/dashboard",
    response_class=HTMLResponse,
)
def dashboard_html() -> str:
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
        <title>Donexto</title>
        <style>
            body {{
                margin: 0;
                padding: 40px 20px;
                background: #0b1020;
                color: #eef2ff;
                font-family: Arial, sans-serif;
            }}
            .container {{
                max-width: 820px;
                margin: 0 auto;
                padding: 32px;
                background: #11182c;
                border: 1px solid #26314f;
                border-radius: 18px;
            }}
            h1 {{ margin-top: 0; }}
            .status {{
                padding: 14px;
                margin: 20px 0;
                background: #18213a;
                border-radius: 10px;
            }}
            a {{
                display: inline-block;
                padding: 12px 18px;
                margin: 6px 6px 6px 0;
                color: white;
                background: #345cff;
                border-radius: 8px;
                text-decoration: none;
            }}
        </style>
    </head>
    <body>
        <main class="container">
            <h1>Donexto</h1>
            <p>
                Plataforma de Inteligencia Operacional basada
                en Casos Inteligentes.
            </p>
            <div class="status">
                <strong>Google Gmail:</strong>
                {connection_status}
                <div>{account_email}</div>
            </div>
            <a href="/auth/google/login">Conectar Google</a>
            <a href="/cases/dashboard">Dashboard de Casos</a>
            <a href="/cases">Casos</a>
            <a href="/messages/stored">Mensajes almacenados</a>
            <a href="/docs">API</a>
        </main>
    </body>
    </html>
    """


gmail_router = create_gmail_router(
    get_active_google_credentials,
)

app.include_router(system_router)
app.include_router(identity_router)
app.include_router(ai_router)
app.include_router(auth_router)
app.include_router(yahoo_mail_router)
app.include_router(gmail_router)
app.include_router(guided_import_router)
app.include_router(sync_jobs_router)
app.include_router(messages_router)
app.include_router(push_router)
app.include_router(cases_router)
