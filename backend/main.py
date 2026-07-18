from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from supabase_client import supabase

app = FastAPI(
    title="HMS AI Assistant API",
    version="0.1.0",
    description="Backend del asistente inteligente de correo",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "HMS AI Assistant API funcionando",
        "version": "0.1.0",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "backend",
    }


@app.get("/database-health")
def database_health():
    try:
        response = (
            supabase.table("mail_accounts")
            .select("id", count="exact")
            .limit(1)
            .execute()
        )

        return {
            "status": "ok",
            "database": "connected",
            "table": "mail_accounts",
            "records": response.count or 0,
        }

    except Exception as error:
        return {
            "status": "error",
            "database": "disconnected",
            "detail": str(error),
        }


@app.get("/dashboard")
def dashboard():
    return {
        "emails_today": 0,
        "unanswered": 0,
        "urgent": 0,
        "tasks": 0,
        "documents_pending": 0,
        "payments_at_risk": 0,
    }