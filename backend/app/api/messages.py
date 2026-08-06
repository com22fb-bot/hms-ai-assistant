from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.services.message_repository import (
    get_stored_conversation,
    get_stored_message,
    list_stored_threads,
)
from app.services.message_rules_service import (
    create_classification_rule,
    deactivate_classification_rule,
    list_classification_rules,
)
from app.services.message_triage_repository import triage_summary
from app.services.message_watch_service import (
    list_watch_rules,
    set_message_watch,
)


router = APIRouter(prefix="/messages", tags=["Stored Messages"])


class FavoriteRequest(BaseModel):
    enabled: bool = True
    match_type: Literal["sender", "subject", "sender_subject"] = "sender"


class ClassificationRuleRequest(BaseModel):
    source_message_id: str
    name: str = Field(default="", max_length=300)
    match_type: Literal[
        "sender",
        "sender_domain",
        "subject_contains",
        "body_contains",
        "sender_subject",
    ]
    target_category: Literal[
        "action_required",
        "review",
        "notice",
        "social",
        "promotional",
        "automated",
        "informational",
    ]
    match_value: str | None = Field(default=None, max_length=1000)
    apply_existing: bool = False
    notify_push: bool = False


@router.get("/triage-summary")
def stored_message_triage_summary(
    limit_per_category: int = Query(default=8, ge=1, le=20),
) -> dict[str, Any]:
    return triage_summary(limit_per_category=limit_per_category)


@router.get("/favorites/rules")
def favorite_rules() -> dict[str, Any]:
    rows = list_watch_rules()
    return {"status": "ok", "total": len(rows), "rules": rows}


@router.get("/rules")
def classification_rules() -> dict[str, Any]:
    rows = list_classification_rules()
    return {"status": "ok", "total": len(rows), "rules": rows}


@router.post("/rules")
def create_rule(payload: ClassificationRuleRequest) -> dict[str, Any]:
    return {
        "status": "ok",
        **create_classification_rule(
            source_message_id=payload.source_message_id,
            name=payload.name,
            match_type=payload.match_type,
            target_category=payload.target_category,
            explicit_value=payload.match_value,
            apply_existing=payload.apply_existing,
            notify_push=payload.notify_push,
        ),
    }


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: str) -> dict[str, Any]:
    return {
        "status": "ok",
        "rule": deactivate_classification_rule(rule_id),
    }


@router.get("/threads")
def stored_threads(
    limit: int = Query(default=40, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    direction: str | None = Query(default=None),
    triage_category: str | None = Query(default=None),
    search: str | None = Query(default=None),
    favorites_only: bool = Query(default=False),
) -> dict[str, Any]:
    return list_stored_threads(
        limit=limit,
        offset=offset,
        direction=direction,
        triage_category=triage_category,
        search=search,
        favorites_only=favorites_only,
    )


@router.get("/stored")
def stored_messages_compatibility(
    limit: int = Query(default=40, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    direction: str | None = Query(default=None),
    triage_category: str | None = Query(default=None),
    search: str | None = Query(default=None),
    favorites_only: bool = Query(default=False),
) -> dict[str, Any]:
    # Compatibilidad: ahora la bandeja principal devuelve conversaciones.
    return list_stored_threads(
        limit=limit,
        offset=offset,
        direction=direction,
        triage_category=triage_category,
        search=search,
        favorites_only=favorites_only,
    )


@router.put("/stored/{message_id}/favorite")
def favorite_message(
    message_id: str,
    payload: FavoriteRequest,
) -> dict[str, Any]:
    return {
        "status": "ok",
        "favorite": set_message_watch(
            message_id=message_id,
            enabled=payload.enabled,
            match_type=payload.match_type,
        ),
    }


@router.get("/stored/{message_id}/conversation")
def stored_conversation(message_id: str) -> dict[str, Any]:
    return get_stored_conversation(message_id)


@router.get("/stored/{message_id}")
def stored_message(message_id: str) -> dict[str, Any]:
    return get_stored_message(message_id)
