from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.security.mutation_guard import require_data_mutations_enabled
from app.schemas.cases import (
    CaseDashboardResponse,
    CaseDetail,
    CaseListResponse,
    CaseProcessResponse,
    CaseUpdateRequest,
    NotificationListResponse,
)
from app.services.case_engine import process_pending_messages
from app.services.case_user_actions import UserCaseAction, apply_user_action
from app.services.case_repository import (
    dashboard,
    get_case,
    list_cases,
    list_notifications,
    update_case,
)


router = APIRouter(
    prefix="/cases",
    tags=["Intelligent Cases"],
)


@router.post(
    "/process",
    response_model=CaseProcessResponse,
)
def process_cases(
    limit: int = Query(default=200, ge=1, le=500),
) -> dict[str, Any]:
    require_data_mutations_enabled("case_processing")
    return process_pending_messages(limit=limit)


@router.get(
    "/dashboard",
    response_model=CaseDashboardResponse,
)
def cases_dashboard() -> dict[str, Any]:
    return dashboard()


@router.get(
    "/notifications",
    response_model=NotificationListResponse,
)
def notifications(
    unread_only: bool = Query(default=True),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    return list_notifications(
        unread_only=unread_only,
        limit=limit,
    )


@router.get(
    "",
    response_model=CaseListResponse,
)
def cases(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    search: str | None = Query(default=None),
) -> dict[str, Any]:
    return list_cases(
        limit=limit,
        offset=offset,
        status=status,
        priority=priority,
        search=search,
    )


@router.get(
    "/{case_id}",
    response_model=CaseDetail,
)
def case_detail(case_id: str) -> dict[str, Any]:
    return get_case(case_id)


@router.patch(
    "/{case_id}",
    response_model=CaseDetail,
)
def patch_case(
    case_id: str,
    request: CaseUpdateRequest,
) -> dict[str, Any]:
    require_data_mutations_enabled("case_update")
    update_case(
        case_id=case_id,
        changes=request.model_dump(exclude_unset=True),
    )

    return get_case(case_id)


class CaseUserActionRequest(BaseModel):
    action: UserCaseAction
    until: datetime | None = None


@router.post(
    "/{case_id}/user-action",
    response_model=CaseDetail,
)
def case_user_action(
    case_id: UUID,
    request: CaseUserActionRequest,
) -> dict[str, Any]:
    """Hecho / posponer / reabrir for the signed-in user's own case.

    Not behind ``require_data_mutations_enabled``: see
    ``app/services/case_user_actions.py`` for why this narrow, per-user,
    allow-listed write is safe during containment (the generic PATCH is not).
    """
    apply_user_action(
        case_id=str(case_id),
        action=request.action,
        until=request.until,
    )
    return get_case(str(case_id))
