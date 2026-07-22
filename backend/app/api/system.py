from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.database.supabase import get_supabase_client


router = APIRouter(
    tags=["System"],
)


@router.get("/health")
def health() -> dict[str, str]:
    """Confirma que el backend está funcionando."""
    return {
        "status": "ok",
        "service": "backend",
        "version": settings.app_version,
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
