from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import HTTPException

from app.security.identity import require_google_account, require_request_context
from app.services.oauth_storage import OAuthStorage
from app.services.web_push_sender import send_web_push


_REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_REPO_ROOT / ".hms-secrets" / "push.env", override=False)


def _rows(response: Any) -> list[dict[str, Any]]:
    data = getattr(response, "data", None)
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def _first(response: Any) -> dict[str, Any] | None:
    rows = _rows(response)
    return rows[0] if rows else None


def _public_key() -> str:
    return os.getenv("HMS_VAPID_PUBLIC_KEY", "").strip()


def _private_key_path() -> str:
    return os.getenv("HMS_VAPID_PRIVATE_KEY_PATH", "").strip()


def _subject() -> str:
    return os.getenv(
        "HMS_VAPID_SUBJECT",
        "mailto:hmcelinfo@gmail.com",
    ).strip()


def push_configuration() -> dict[str, Any]:
    return {
        "configured": bool(_public_key() and _private_key_path()),
        "public_key": _public_key(),
        "sender_available": True,
    }


def save_subscription(
    *,
    endpoint: str,
    p256dh: str,
    auth_secret: str,
    user_agent: str | None,
    device_label: str | None,
) -> dict[str, Any]:
    context = require_request_context()
    client = OAuthStorage().client
    clean_endpoint = endpoint.strip()
    if not clean_endpoint or not p256dh.strip() or not auth_secret.strip():
        raise HTTPException(
            status_code=422,
            detail={
                "status": "invalid_subscription",
                "message": "El navegador no devolvió una suscripción push completa.",
            },
        )

    existing = _first(
        client.table("push_subscriptions")
        .select("*")
        .eq("profile_id", context.user.id)
        .eq("endpoint", clean_endpoint)
        .limit(1)
        .execute()
    )
    payload = {
        "workspace_id": context.workspace_id,
        "profile_id": context.user.id,
        "endpoint": clean_endpoint,
        "p256dh": p256dh.strip(),
        "auth_secret": auth_secret.strip(),
        "user_agent": (user_agent or "")[:1000] or None,
        "device_label": (device_label or "Este dispositivo")[:200],
        "is_active": True,
        "last_seen_at": "now()",
        "updated_at": "now()",
        "last_error": None,
    }
    if existing:
        updated = _first(
            client.table("push_subscriptions")
            .update(payload)
            .eq("id", str(existing["id"]))
            .execute()
        )
        return updated or {**existing, **payload}

    created = _first(
        client.table("push_subscriptions").insert(payload).execute()
    )
    if not created:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "subscription_not_saved",
                "message": "Supabase no confirmó el dispositivo.",
            },
        )
    return created


def deactivate_subscription(endpoint: str) -> int:
    context = require_request_context()
    response = (
        OAuthStorage().client.table("push_subscriptions")
        .update({"is_active": False, "updated_at": "now()"})
        .eq("profile_id", context.user.id)
        .eq("endpoint", endpoint.strip())
        .execute()
    )
    return len(_rows(response))


def list_profile_subscriptions(profile_id: str) -> list[dict[str, Any]]:
    return _rows(
        OAuthStorage().client.table("push_subscriptions")
        .select(
            "id,endpoint,device_label,user_agent,is_active,last_seen_at,"
            "last_success_at,last_error,created_at"
        )
        .eq("profile_id", profile_id)
        .order("created_at", desc=True)
        .execute()
    )


def _deliver_to_profile(
    *,
    profile_id: str,
    notification_id: str,
    payload: dict[str, Any],
    target_endpoint: str | None = None,
) -> dict[str, int]:
    client = OAuthStorage().client
    subscriptions = _rows(
        client.table("push_subscriptions")
        .select("*")
        .eq("profile_id", profile_id)
        .eq("is_active", True)
        .execute()
    )
    if target_endpoint:
        clean_target = target_endpoint.strip()
        subscriptions = [
            row
            for row in subscriptions
            if str(row.get("endpoint") or "").strip() == clean_target
        ]
    result = {"devices": len(subscriptions), "sent": 0, "failed": 0, "expired": 0}
    if not subscriptions:
        return result
    if not _private_key_path() or not _public_key():
        result["failed"] = len(subscriptions)
        return result

    for subscription in subscriptions:
        status = "sent"
        http_status: int | None = None
        error_text: str | None = None
        try:
            response = send_web_push(
                endpoint=str(subscription["endpoint"]),
                p256dh=str(subscription["p256dh"]),
                auth_secret=str(subscription["auth_secret"]),
                payload=payload,
                vapid_private_key_path=_private_key_path(),
                vapid_public_key=_public_key(),
                vapid_subject=_subject(),
                ttl=900,
                timeout=12,
            )
            http_status = int(response.status_code)
            if 200 <= http_status < 300:
                result["sent"] += 1
                client.table("push_subscriptions").update(
                    {
                        "last_success_at": "now()",
                        "last_seen_at": "now()",
                        "last_error": None,
                        "updated_at": "now()",
                    }
                ).eq("id", str(subscription["id"])).execute()
            elif http_status in {404, 410}:
                status = "expired"
                error_text = response.text[:1500]
                result["expired"] += 1
                client.table("push_subscriptions").update(
                    {
                        "is_active": False,
                        "last_error": error_text,
                        "updated_at": "now()",
                    }
                ).eq("id", str(subscription["id"])).execute()
            else:
                status = "failed"
                error_text = response.text[:1500] or f"HTTP {http_status}"
                result["failed"] += 1
                client.table("push_subscriptions").update(
                    {"last_error": error_text, "updated_at": "now()"}
                ).eq("id", str(subscription["id"])).execute()
        except Exception as error:  # pragma: no cover - proveedor externo
            status = "failed"
            error_text = str(error)[:1500]
            result["failed"] += 1

        client.table("push_delivery_log").insert(
            {
                "notification_id": notification_id,
                "subscription_id": str(subscription["id"]),
                "status": status,
                "http_status": http_status,
                "error_text": error_text,
            }
        ).execute()
    return result


def create_notification(
    *,
    workspace_id: str,
    profile_id: str,
    notification_type: str,
    title: str,
    body: str,
    dedupe_key: str,
    account_id: str | None = None,
    message_id: str | None = None,
    case_id: str | None = None,
    url: str = "/",
    send_push: bool = True,
    target_endpoint: str | None = None,
) -> dict[str, Any]:
    client = OAuthStorage().client
    existing = _first(
        client.table("hms_notifications")
        .select("*")
        .eq("profile_id", profile_id)
        .eq("dedupe_key", dedupe_key)
        .limit(1)
        .execute()
    )
    if existing:
        return {"notification": existing, "delivery": {"deduplicated": 1}}

    notification = _first(
        client.table("hms_notifications")
        .insert(
            {
                "workspace_id": workspace_id,
                "account_id": account_id,
                "profile_id": profile_id,
                "notification_type": notification_type,
                "title": title[:300],
                "body": body[:1000],
                "url": url[:1000] or "/",
                "message_id": message_id,
                "case_id": case_id,
                "dedupe_key": dedupe_key[:500],
            }
        )
        .execute()
    )
    if not notification:
        raise RuntimeError("Supabase no confirmó la notificación HMS.")

    delivery: dict[str, Any] = {"devices": 0, "sent": 0, "failed": 0, "expired": 0}
    if send_push:
        delivery = _deliver_to_profile(
            profile_id=profile_id,
            notification_id=str(notification["id"]),
            payload={
                "title": title,
                "body": body,
                "url": url or "/",
                "notificationId": str(notification["id"]),
                "type": notification_type,
            },
            target_endpoint=target_endpoint,
        )
        if int(delivery.get("sent") or 0) > 0:
            client.table("hms_notifications").update(
                {"pushed_at": "now()"}
            ).eq("id", str(notification["id"])).execute()
    return {"notification": notification, "delivery": delivery}


def notification_status() -> dict[str, Any]:
    context = require_request_context()
    client = OAuthStorage().client
    subscriptions = list_profile_subscriptions(context.user.id)
    unread = _rows(
        client.table("hms_notifications")
        .select("id")
        .eq("profile_id", context.user.id)
        .is_("read_at", "null")
        .execute()
    )
    return {
        **push_configuration(),
        "devices": len([row for row in subscriptions if row.get("is_active")]),
        "subscriptions": subscriptions,
        "unread": len(unread),
    }


def list_notifications(limit: int = 30) -> list[dict[str, Any]]:
    context = require_request_context()
    return _rows(
        OAuthStorage().client.table("hms_notifications")
        .select("*")
        .eq("profile_id", context.user.id)
        .order("created_at", desc=True)
        .limit(min(max(limit, 1), 100))
        .execute()
    )


def mark_notification_read(notification_id: str) -> dict[str, Any] | None:
    context = require_request_context()
    return _first(
        OAuthStorage().client.table("hms_notifications")
        .update({"read_at": "now()"})
        .eq("profile_id", context.user.id)
        .eq("id", notification_id)
        .execute()
    )


def send_test_notification(endpoint: str | None = None) -> dict[str, Any]:
    context, account = require_google_account()
    if not _public_key() or not _private_key_path():
        raise HTTPException(
            status_code=503,
            detail={
                "status": "push_not_configured",
                "message": "Las llaves VAPID todavía no están configuradas.",
            },
        )
    target = (endpoint or "").strip() or None
    device_scope = (
        "este dispositivo"
        if target
        else "todos los dispositivos activos"
    )
    return create_notification(
        workspace_id=context.workspace_id,
        account_id=str(account["id"]),
        profile_id=context.user.id,
        notification_type="push_test",
        title="HMS está listo",
        body=(
            f"Prueba de notificaciones hacia {device_scope}. "
            "Aqui veras avisos de favoritos y asuntos accionables."
        ),
        dedupe_key=f"push-test:{context.user.id}:{os.urandom(8).hex()}",
        url="/",
        send_push=True,
        target_endpoint=target,
    )


def notify_actionable_messages(
    *,
    account_id: str,
    workspace_id: str,
    limit: int = 100,
) -> dict[str, int]:
    client = OAuthStorage().client
    messages = _rows(
        client.table("communication_messages")
        .select("id,sender,subject,snippet,body_text,received_at")
        .eq("account_id", account_id)
        .eq("direction", "inbound")
        .eq("triage_category", "action_required")
        .is_("push_notified_at", "null")
        .order("received_at", desc=False)
        .limit(min(max(limit, 1), 500))
        .execute()
    )
    members = _rows(
        client.table("workspace_members")
        .select("profile_id")
        .eq("workspace_id", workspace_id)
        .eq("status", "active")
        .execute()
    )
    sent_notifications = 0
    for message in messages:
        message_id = str(message["id"])
        subject = str(message.get("subject") or "Correo que requiere atención")
        sender = str(message.get("sender") or "Remitente no identificado")
        snippet = " ".join(
            str(message.get("snippet") or message.get("body_text") or "").split()
        )[:220]
        for member in members:
            profile_id = str(member.get("profile_id") or "")
            if not profile_id:
                continue
            create_notification(
                workspace_id=workspace_id,
                account_id=account_id,
                profile_id=profile_id,
                notification_type="action_required",
                title=subject,
                body=f"{sender}. {snippet}"[:1000],
                dedupe_key=f"action-required:{message_id}",
                message_id=message_id,
                url=f"/?mail={message_id}",
                send_push=True,
            )
            sent_notifications += 1
        client.table("communication_messages").update(
            {"push_notified_at": "now()"}
        ).eq("id", message_id).execute()
    return {"messages": len(messages), "notifications": sent_notifications}
