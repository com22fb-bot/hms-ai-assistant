from __future__ import annotations

from email.utils import getaddresses
from typing import Any

from fastapi import HTTPException

from app.security.identity import require_google_account
from app.services.case_engine import normalize_subject
from app.services.oauth_storage import OAuthStorage
from app.services.push_service import create_notification


WATCH_MODES = {"sender", "subject", "sender_subject"}


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


def _sender_email(value: str | None) -> str:
    addresses = getaddresses([value or ""])
    if not addresses:
        return ""
    return addresses[0][1].strip().lower()


def _message_or_404(
    *,
    client: Any,
    account_id: str,
    message_id: str,
) -> dict[str, Any]:
    message = _first(
        client.table("communication_messages")
        .select("id,account_id,sender,subject,normalized_subject")
        .eq("account_id", account_id)
        .eq("id", message_id)
        .limit(1)
        .execute()
    )
    if not message:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "not_found",
                "message": "El correo seleccionado no existe en HMS.",
            },
        )
    return message


def set_message_watch(
    *,
    message_id: str,
    enabled: bool,
    match_type: str,
) -> dict[str, Any]:
    context, account = require_google_account()
    if match_type not in WATCH_MODES:
        raise HTTPException(
            status_code=422,
            detail={
                "status": "invalid_watch_mode",
                "message": "Elige remitente, tema o remitente y tema.",
            },
        )

    storage = OAuthStorage()
    client = storage.client
    account_id = str(account["id"])
    message = _message_or_404(
        client=client,
        account_id=account_id,
        message_id=message_id,
    )
    sender_email = _sender_email(message.get("sender"))
    normalized_subject = (
        str(message.get("normalized_subject") or "").strip()
        or normalize_subject(str(message.get("subject") or ""))
    )

    if enabled and match_type in {"sender", "sender_subject"} and not sender_email:
        raise HTTPException(
            status_code=422,
            detail={
                "status": "sender_required",
                "message": "No fue posible identificar el correo del remitente.",
            },
        )

    if enabled and match_type in {"subject", "sender_subject"} and not normalized_subject:
        raise HTTPException(
            status_code=422,
            detail={
                "status": "subject_required",
                "message": "Este mensaje no contiene un tema utilizable.",
            },
        )

    existing = _first(
        client.table("message_watch_rules")
        .select("*")
        .eq("profile_id", context.user.id)
        .eq("source_message_id", message_id)
        .limit(1)
        .execute()
    )

    payload = {
        "workspace_id": context.workspace_id,
        "account_id": account_id,
        "profile_id": context.user.id,
        "source_message_id": message_id,
        "match_type": match_type,
        "sender_email": sender_email or None,
        "normalized_subject": normalized_subject or None,
        "display_label": str(message.get("subject") or sender_email or "Favorito")[:500],
        "is_active": enabled,
        "notify_in_app": True,
        "notify_push": True,
        "updated_at": "now()",
    }

    if existing:
        payload.pop("updated_at", None)
        updated = _first(
            client.table("message_watch_rules")
            .update(payload)
            .eq("id", str(existing["id"]))
            .execute()
        )
        return updated or {**existing, **payload}

    payload.pop("updated_at", None)
    created = _first(
        client.table("message_watch_rules")
        .insert(payload)
        .execute()
    )
    if not created:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "favorite_not_saved",
                "message": "Supabase no confirmó el favorito.",
            },
        )
    return created


def list_watch_rules() -> list[dict[str, Any]]:
    context, account = require_google_account()
    return _rows(
        OAuthStorage().client.table("message_watch_rules")
        .select("*")
        .eq("profile_id", context.user.id)
        .eq("account_id", str(account["id"]))
        .order("created_at", desc=True)
        .execute()
    )


def _rule_matches(
    rule: dict[str, Any],
    message: dict[str, Any],
) -> bool:
    sender_matches = _sender_email(message.get("sender")) == str(
        rule.get("sender_email") or ""
    ).lower()
    subject_matches = str(
        message.get("normalized_subject")
        or normalize_subject(str(message.get("subject") or ""))
    ) == str(rule.get("normalized_subject") or "")
    mode = str(rule.get("match_type") or "")

    if mode == "sender":
        return sender_matches
    if mode == "subject":
        return subject_matches
    if mode == "sender_subject":
        return sender_matches and subject_matches
    return False


def match_watch_rules_for_account(
    *,
    account_id: str,
    workspace_id: str,
) -> dict[str, int]:
    client = OAuthStorage().client
    rules = _rows(
        client.table("message_watch_rules")
        .select("*")
        .eq("account_id", account_id)
        .eq("workspace_id", workspace_id)
        .eq("is_active", True)
        .execute()
    )
    created_matches = 0

    for rule in rules:
        messages = _rows(
            client.table("communication_messages")
            .select(
                "id,sender,subject,normalized_subject,created_at,direction"
            )
            .eq("account_id", account_id)
            .eq("direction", "inbound")
            .gte("created_at", str(rule.get("created_at")))
            .order("created_at", desc=False)
            .limit(500)
            .execute()
        )
        existing_ids = {
            str(row.get("message_id"))
            for row in _rows(
                client.table("message_watch_matches")
                .select("message_id")
                .eq("rule_id", str(rule["id"]))
                .execute()
            )
        }

        for message in messages:
            message_id = str(message.get("id") or "")
            if (
                not message_id
                or message_id == str(rule.get("source_message_id") or "")
                or message_id in existing_ids
                or not _rule_matches(rule, message)
            ):
                continue

            try:
                match = _first(
                    client.table("message_watch_matches").insert(
                        {
                            "rule_id": str(rule["id"]),
                            "message_id": message_id,
                        }
                    ).execute()
                )
                created_matches += 1
                subject = str(message.get("subject") or "Correo favorito recibido")
                sender = str(message.get("sender") or "Remitente no identificado")
                notification = create_notification(
                    workspace_id=workspace_id,
                    account_id=account_id,
                    profile_id=str(rule["profile_id"]),
                    notification_type="favorite_match",
                    title=subject,
                    body=f"Llegó un nuevo correo de {sender} que coincide con tu favorito.",
                    dedupe_key=f"favorite:{rule['id']}:{message_id}",
                    message_id=message_id,
                    url=f"/?mail={message_id}",
                    send_push=bool(rule.get("notify_push")),
                )
                if match and notification.get("delivery"):
                    client.table("message_watch_matches").update(
                        {"notified_at": "now()"}
                    ).eq("id", str(match["id"])).execute()
            except Exception:
                # La restricción única protege contra reintentos.
                pass

    return {
        "rules": len(rules),
        "matches_created": created_matches,
    }
