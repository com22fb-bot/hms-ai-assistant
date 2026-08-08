from __future__ import annotations

from fastapi import HTTPException

from app.core.config import settings


def require_data_mutations_enabled(operation: str) -> None:
    """Bloquea escrituras de datos mientras HMS está en contención."""
    if settings.data_mutations_enabled:
        return

    raise HTTPException(
        status_code=423,
        detail={
            "status": "data_mutations_locked",
            "operation": operation,
            "message": (
                "Esta operación permanece bloqueada mientras HMS valida "
                "la integridad de los datos históricos."
            ),
            "configuration": "HMS_DATA_MUTATIONS_ENABLED=false",
        },
    )
