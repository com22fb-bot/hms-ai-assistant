from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.database.supabase import get_supabase_client


router = APIRouter(
    tags=["System"],
)


def _env_is_set(name: str) -> bool:
    return bool(os.getenv(name, "").strip())


@router.get("/health")
def health() -> dict[str, Any]:
    """Confirma disponibilidad y estado de contención."""
    return {
        "status": "ok",
        "service": "backend",
        "version": settings.app_version,
        "data_mutations_enabled": settings.data_mutations_enabled,
        "data_mode": (
            "read_write"
            if settings.data_mutations_enabled
            else "inventory_read_only"
        ),
    }


@router.get("/env-status")
def env_status() -> dict[str, Any]:
    """Indica si hay variables requeridas (solo booleanos; nunca secretos)."""
    redirect = os.getenv("GOOGLE_REDIRECT_URI", "").strip().lower()
    origins = os.getenv("FRONTEND_ORIGINS", "").strip().lower()

    redirect_is_codespace = (
        "github.dev" in redirect or "githubpreview.dev" in redirect
    )
    redirect_is_railway = (
        "railway.app" in redirect and "/auth/google/callback" in redirect
    )
    frontend_is_donexto = "donexto.com" in origins
    oauth_ready_for_donexto = (
        _env_is_set("GOOGLE_CLIENT_ID")
        and _env_is_set("GOOGLE_CLIENT_SECRET")
        and redirect_is_railway
        and not redirect_is_codespace
        and frontend_is_donexto
    )

    return {
        "status": "ok",
        "version": settings.app_version,
        "product": "Donexto",
        "app_version_code": settings.app_version,
        "variables_present": {
            "GOOGLE_CLIENT_ID": _env_is_set("GOOGLE_CLIENT_ID"),
            "GOOGLE_CLIENT_SECRET": _env_is_set("GOOGLE_CLIENT_SECRET"),
            "GOOGLE_REDIRECT_URI": _env_is_set("GOOGLE_REDIRECT_URI"),
            "OAUTH_ENCRYPTION_KEY": _env_is_set("OAUTH_ENCRYPTION_KEY"),
            "SUPABASE_URL": _env_is_set("SUPABASE_URL"),
            "SUPABASE_SECRET_KEY": _env_is_set("SUPABASE_SECRET_KEY"),
            "FRONTEND_ORIGINS": _env_is_set("FRONTEND_ORIGINS"),
            "HMS_DATA_MUTATIONS_ENABLED": _env_is_set(
                "HMS_DATA_MUTATIONS_ENABLED"
            ),
            "YAHOO_CLIENT_ID": _env_is_set("YAHOO_CLIENT_ID"),
            "YAHOO_CLIENT_SECRET": _env_is_set("YAHOO_CLIENT_SECRET"),
            "YAHOO_REDIRECT_URI": _env_is_set("YAHOO_REDIRECT_URI"),
            "AZURE_CLIENT_ID": _env_is_set("AZURE_CLIENT_ID"),
            "AZURE_CLIENT_SECRET": _env_is_set("AZURE_CLIENT_SECRET"),
            "AZURE_REDIRECT_URI": _env_is_set("AZURE_REDIRECT_URI"),
            "SUPPORT_NOTIFY_EMAIL": _env_is_set("SUPPORT_NOTIFY_EMAIL"),
            "SUPPORT_SMTP_HOST": _env_is_set("SUPPORT_SMTP_HOST"),
        },
        "oauth_shape": {
            "frontend_mentions_donexto": frontend_is_donexto,
            "redirect_is_railway_callback": redirect_is_railway,
            "redirect_is_codespace": redirect_is_codespace,
            "encryption_key_present": _env_is_set("OAUTH_ENCRYPTION_KEY"),
            "ready_for_donexto_gmail": oauth_ready_for_donexto
            and _env_is_set("OAUTH_ENCRYPTION_KEY"),
        },
    }


@router.get("/database-health")
def database_health() -> dict[str, Any]:
    """Comprueba la conexión con Supabase y la tabla mail_accounts."""
    try:
        supabase = get_supabase_client()

        response = (
            supabase.table("mail_accounts")
            .select("*", count="exact")
            .limit(1)
            .execute()
        )

        record_count = (
            response.count
            if response.count is not None
            else 0
        )

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
                "message": (
                    "No fue posible establecer conexión "
                    "con Supabase."
                ),
                "technical_detail": str(error),
            },
        ) from error
