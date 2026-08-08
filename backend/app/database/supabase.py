from __future__ import annotations

from fastapi import HTTPException
from supabase import Client, create_client

from app.core.config import settings


def validate_supabase_environment() -> None:
    """Verifica que las variables necesarias de Supabase existan."""
    missing_variables: list[str] = []

    if not settings.supabase_url:
        missing_variables.append("SUPABASE_URL")

    if not settings.supabase_secret_key:
        missing_variables.append("SUPABASE_SECRET_KEY")

    if missing_variables:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": (
                    "Faltan variables de Supabase "
                    "en el entorno."
                ),
                "missing_variables": missing_variables,
            },
        )


def get_supabase_client() -> Client:
    """Crea y devuelve un cliente configurado de Supabase."""
    validate_supabase_environment()

    return create_client(
        settings.supabase_url,
        settings.supabase_secret_key,
    )