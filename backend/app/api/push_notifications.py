from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, Query
from pydantic import BaseModel, Field

from app.services.push_service import (
    deactivate_subscription,
    list_notifications,
    mark_notification_read,
    notification_status,
    push_configuration,
    save_subscription,
    send_test_notification,
)


router = APIRouter(prefix="/push", tags=["Push Notifications"])


class SubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class SubscriptionRequest(BaseModel):
    endpoint: str
    keys: SubscriptionKeys
    device_label: str | None = Field(default=None, max_length=200)


class DeactivateRequest(BaseModel):
    endpoint: str


@router.get("/vapid-public-key")
def vapid_public_key() -> dict[str, Any]:
    return {"status": "ok", **push_configuration()}


@router.get("/status")
def push_status() -> dict[str, Any]:
    return {"status": "ok", **notification_status()}


@router.post("/subscriptions")
def subscribe_device(
    payload: SubscriptionRequest,
    user_agent: str | None = Header(default=None),
) -> dict[str, Any]:
    subscription = save_subscription(
        endpoint=payload.endpoint,
        p256dh=payload.keys.p256dh,
        auth_secret=payload.keys.auth,
        user_agent=user_agent,
        device_label=payload.device_label,
    )
    return {"status": "ok", "subscription": subscription}


@router.post("/subscriptions/deactivate")
def unsubscribe_device(payload: DeactivateRequest) -> dict[str, Any]:
    return {
        "status": "ok",
        "deactivated": deactivate_subscription(payload.endpoint),
    }


@router.post("/test")
def test_push() -> dict[str, Any]:
    return {"status": "ok", **send_test_notification()}


@router.get("/notifications")
def notifications(
    limit: int = Query(default=30, ge=1, le=100),
) -> dict[str, Any]:
    rows = list_notifications(limit=limit)
    return {"status": "ok", "total": len(rows), "notifications": rows}


@router.patch("/notifications/{notification_id}/read")
def read_notification(notification_id: str) -> dict[str, Any]:
    return {
        "status": "ok",
        "notification": mark_notification_read(notification_id),
    }
