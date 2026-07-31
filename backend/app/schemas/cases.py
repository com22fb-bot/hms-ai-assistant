from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


CaseStatus = Literal[
    "new",
    "analyzing",
    "in_progress",
    "delegated",
    "waiting_internal",
    "waiting_external",
    "resolved",
    "closed",
    "archived",
]

CasePriority = Literal[
    "low",
    "normal",
    "high",
    "critical",
]

WaitingOn = Literal[
    "internal",
    "external",
    "none",
]


class CaseEventResponse(BaseModel):
    id: UUID
    case_id: UUID
    message_id: UUID | None = None
    event_type: str
    level: int = Field(ge=0, le=4)
    title: str
    description: str | None = None
    actor_type: str
    actor_identifier: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class CaseListItem(BaseModel):
    id: UUID
    title: str
    case_type: str
    status: CaseStatus
    priority: CasePriority
    risk_score: int = Field(ge=0, le=100)
    confidence: float
    summary: str | None = None
    requested_action: str | None = None
    requester_name: str | None = None
    requester_email: str | None = None
    current_owner_email: str | None = None
    waiting_on: WaitingOn
    opened_at: datetime
    last_activity_at: datetime
    due_at: datetime | None = None
    resolved_at: datetime | None = None
    source_count: int
    reminder_count: int


class CaseDetail(CaseListItem):
    workspace_id: UUID
    account_id: UUID | None = None
    primary_thread_id: UUID | None = None
    normalized_subject: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    participants: list[dict[str, Any]] = Field(default_factory=list)
    messages: list[dict[str, Any]] = Field(default_factory=list)
    events: list[CaseEventResponse] = Field(default_factory=list)


class CaseListResponse(BaseModel):
    status: str = "ok"
    total: int
    limit: int
    offset: int
    cases: list[CaseListItem]


class CaseDashboardMetrics(BaseModel):
    total_open: int = 0
    critical: int = 0
    waiting_internal: int = 0
    waiting_external: int = 0
    overdue: int = 0
    resolved_today: int = 0
    unread_notifications: int = 0


class CaseDashboardResponse(BaseModel):
    status: str = "ok"
    metrics: CaseDashboardMetrics
    attention: list[CaseListItem] = Field(default_factory=list)
    recent_events: list[CaseEventResponse] = Field(default_factory=list)


class CaseProcessResponse(BaseModel):
    status: str
    account_id: UUID
    requested_limit: int
    found: int
    processed: int
    created_cases: int
    linked_to_existing: int
    errors: int
    error_details: list[dict[str, str]] = Field(default_factory=list)


class CaseUpdateRequest(BaseModel):
    status: CaseStatus | None = None
    priority: CasePriority | None = None
    current_owner_email: str | None = None
    waiting_on: WaitingOn | None = None
    due_at: datetime | None = None
    summary: str | None = None
    requested_action: str | None = None


class NotificationListResponse(BaseModel):
    status: str = "ok"
    total: int
    notifications: list[dict[str, Any]] = Field(default_factory=list)
