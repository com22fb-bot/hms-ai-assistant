"""
Endpoints del motor de análisis inteligente.

HMS AI Assistant
Sprint 3.2
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from app.security.mutation_guard import require_data_mutations_enabled
from app.services.ai_analyzer import analyze_pending_messages


router = APIRouter(
    prefix="/ai",
    tags=["AI"],
)


@router.post(
    "/analyze-pending",
    response_model=None,
)
def analyze_pending(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description=(
            "Cantidad máxima de correos pendientes "
            "que serán analizados."
        ),
    ),
) -> dict[str, Any]:
    require_data_mutations_enabled("ai_analysis")
    return analyze_pending_messages(
        limit=limit,
    )
