from __future__ import annotations

import unicodedata
from datetime import datetime, timezone
from email.utils import getaddresses
from typing import Any

from fastapi import HTTPException

from app.security.identity import require_google_account
from app.services.case_engine import normalize_subject, process_message
from app.services.oauth_storage import OAuthStorage
from app.services.push_service import create_notification


RULE_TYPES = {
    "sender",
    "sender_domain",
    "subject_contains",
    "body_contains",
    "sender_subject",
}
RULE_CATEGORIES = {
    "action_required",
    "review",
    "notice",
    "social",
    "promotional",
    "automated",
    "informational",
}


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


def _norm(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return " ".join(
        "".join(ch for ch in text if not unicodedata.combining(ch))
        .casefold()
        .split()
    )


def _sender_email(value: Any) -> str:
    addresses = getaddresses([str(value or "")])
    return addresses[0][1].strip().lower() if addresses else ""


def _sender_domain(value: Any) -> str:
    email = _sender_email(value)
    return email.rsplit("@", 1)[1] if "@" in email else ""


def _rule_matches(rule: dict[str, Any], message: dict[str, Any]) -> bool:
    rule_type = str(rule.get("match_type") or "")
    primary = _norm(rule.get("match_value"))
    secondary = _norm(rule.get("secondary_value"))
    sender = _norm(_sender_email(message.get("sender")))
    domain = _norm(_sender_domain(message.get("sender")))
    subject = _norm(
        message.get("normalized_subject")
        or normalize_subject(str(message.get("subject") or ""))
    )
    body = _norm(
        " ".join(
            [
                str(message.get("subject") or ""),
                str(message.get("snippet") or ""),
                str(message.get("body_text") or ""),
            ]
        )
    )

    if rule_type == "sender":
        return bool(primary and sender == primary)
    if rule_type == "sender_domain":
        return bool(primary and domain == primary)
    if rule_type == "subject_contains":
        return bool(primary and primary in subject)
    if rule_type == "body_contains":
        return bool(primary and primary in body)
    if rule_type == "sender_subject":
        return bool(primary and secondary and sender == primary and secondary in subject)
    return False


def _message_or_404(
    *,
    client: Any,
    account_id: str,
    message_id: str,
) -> dict[str, Any]:
    message = _first(
        client.table("communication_messages")
        .select("*")
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


def list_classification_rules() -> list[dict[str, Any]]:
    context, account = require_google_account()
    return _rows(
        OAuthStorage().client.table("message_classification_rules")
        .select("*")
        .eq("profile_id", context.user.id)
        .eq("account_id", str(account["id"]))
        .order("priority", desc=False)
        .order("created_at", desc=True)
        .execute()
    )


def _derived_values(
    *,
    message: dict[str, Any],
    match_type: str,
    explicit_value: str | None,
) -> tuple[str, str | None]:
    sender = _sender_email(message.get("sender"))
    subject = str(
        message.get("normalized_subject")
        or normalize_subject(str(message.get("subject") or ""))
    ).strip()
    if match_type == "sender":
        primary, secondary = sender, None
    elif match_type == "sender_domain":
        primary, secondary = _sender_domain(message.get("sender")), None
    elif match_type == "subject_contains":
        primary, secondary = explicit_value or subject, None
    elif match_type == "body_contains":
        primary, secondary = explicit_value or "", None
    elif match_type == "sender_subject":
        primary, secondary = sender, explicit_value or subject
    else:
        primary, secondary = "", None
    if not primary or (match_type == "sender_subject" and not secondary):
        raise HTTPException(
            status_code=422,
            detail={
                "status": "rule_value_required",
                "message": "No fue posible obtener el criterio para esta regla.",
            },
        )
    return primary[:1000], secondary[:1000] if secondary else None


def create_classification_rule(
    *,
    source_message_id: str,
    name: str,
    match_type: str,
    target_category: str,
    explicit_value: str | None,
    apply_existing: bool,
    notify_push: bool,
) -> dict[str, Any]:
    context, account = require_google_account()
    if match_type not in RULE_TYPES:
        raise HTTPException(status_code=422, detail="Tipo de regla no válido.")
    if target_category not in RULE_CATEGORIES:
        raise HTTPException(status_code=422, detail="Categoría de destino no válida.")

    client = OAuthStorage().client
    account_id = str(account["id"])
    message = _message_or_404(
        client=client,
        account_id=account_id,
        message_id=source_message_id,
    )
    primary, secondary = _derived_values(
        message=message,
        match_type=match_type,
        explicit_value=explicit_value,
    )
    created = _first(
        client.table("message_classification_rules")
        .insert(
            {
                "workspace_id": context.workspace_id,
                "account_id": account_id,
                "profile_id": context.user.id,
                "source_message_id": source_message_id,
                "name": (name.strip() or f"Regla para {message.get('subject') or 'correo'}")[:300],
                "match_type": match_type,
                "match_value": primary,
                "secondary_value": secondary,
                "target_category": target_category,
                "notify_push": bool(notify_push),
                "is_active": True,
            }
        )
        .execute()
    )
    if not created:
        raise HTTPException(status_code=503, detail="Supabase no confirmó la regla.")

    applied = {"matched": 0, "updated": 0, "cases_created": 0, "cases_removed": 0}
    if apply_existing:
        applied = apply_rule_to_existing(rule=created)
    return {"rule": created, "applied": applied}


def deactivate_classification_rule(rule_id: str) -> dict[str, Any] | None:
    context, account = require_google_account()
    return _first(
        OAuthStorage().client.table("message_classification_rules")
        .update({"is_active": False, "updated_at": "now()"})
        .eq("id", rule_id)
        .eq("profile_id", context.user.id)
        .eq("account_id", str(account["id"]))
        .execute()
    )


def _unlink_message_cases(client: Any, message_id: str) -> int:
    links = _rows(
        client.table("case_messages")
        .select("case_id")
        .eq("message_id", message_id)
        .execute()
    )
    case_ids = [str(row["case_id"]) for row in links if row.get("case_id")]
    client.table("case_messages").delete().eq("message_id", message_id).execute()
    removed = 0
    for case_id in case_ids:
        remaining = _rows(
            client.table("case_messages")
            .select("message_id")
            .eq("case_id", case_id)
            .limit(1)
            .execute()
        )
        if not remaining:
            client.table("intelligent_cases").delete().eq("id", case_id).execute()
            removed += 1
    return removed


def _apply_rule_to_message(
    *,
    client: Any,
    rule: dict[str, Any],
    message: dict[str, Any],
    workspace_id: str,
    account_id: str,
) -> dict[str, int]:
    category = str(rule["target_category"])
    message_id = str(message["id"])
    now = datetime.now(timezone.utc).isoformat()
    result = {"updated": 0, "cases_created": 0, "cases_removed": 0}

    if category == "action_required":
        client.table("communication_messages").update(
            {
                "classification_rule_id": str(rule["id"]),
                "triage_category": category,
                "actionability_score": 100,
                "triage_reason": f"Clasificado por la regla: {rule.get('name')}",
                "triaged_at": now,
                "case_processed": False,
                "processed_at": None,
            }
        ).eq("id", message_id).execute()
        _, case_status = process_message(
            client=client,
            workspace_id=workspace_id,
            account_id=account_id,
            message=message,
        )
        client.table("communication_messages").update(
            {
                "classification_rule_id": str(rule["id"]),
                "triage_category": category,
                "actionability_score": 100,
                "triage_reason": f"Clasificado por la regla: {rule.get('name')}",
                "triaged_at": now,
                "case_processed": True,
                "processed_at": now,
            }
        ).eq("id", message_id).execute()
        result["cases_created"] = int(case_status == "created")
    else:
        result["cases_removed"] = _unlink_message_cases(client, message_id)
        client.table("communication_messages").update(
            {
                "classification_rule_id": str(rule["id"]),
                "triage_category": category,
                "actionability_score": 0,
                "triage_reason": f"Clasificado por la regla: {rule.get('name')}",
                "triaged_at": now,
                "case_processed": True,
                "processed_at": now,
            }
        ).eq("id", message_id).execute()

    result["updated"] = 1
    if bool(rule.get("notify_push")):
        create_notification(
            workspace_id=workspace_id,
            account_id=account_id,
            profile_id=str(rule["profile_id"]),
            notification_type="classification_rule",
            title=str(message.get("subject") or "Correo clasificado por regla"),
            body=f"La regla “{rule.get('name')}” lo clasificó como {category}.",
            dedupe_key=f"classification-rule:{rule['id']}:{message_id}",
            message_id=message_id,
            url=f"/?mail={message_id}",
            send_push=True,
        )
    return result


def _messages_for_account(client: Any, account_id: str, *, only_unprocessed: bool) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    while offset < 5000:
        query = (
            client.table("communication_messages")
            .select("*")
            .eq("account_id", account_id)
            .order("received_at", desc=False)
            .range(offset, offset + 499)
        )
        if only_unprocessed:
            query = query.eq("case_processed", False)
        page = _rows(query.execute())
        rows.extend(page)
        if len(page) < 500:
            break
        offset += 500
    return rows


def apply_rule_to_existing(*, rule: dict[str, Any]) -> dict[str, int]:
    client = OAuthStorage().client
    account_id = str(rule["account_id"])
    workspace_id = str(rule["workspace_id"])
    totals = {"matched": 0, "updated": 0, "cases_created": 0, "cases_removed": 0}
    for message in _messages_for_account(client, account_id, only_unprocessed=False):
        if not _rule_matches(rule, message):
            continue
        totals["matched"] += 1
        applied = _apply_rule_to_message(
            client=client,
            rule=rule,
            message=message,
            workspace_id=workspace_id,
            account_id=account_id,
        )
        for key in ("updated", "cases_created", "cases_removed"):
            totals[key] += int(applied.get(key) or 0)
    return totals


def apply_active_rules_to_unprocessed_messages(
    *,
    account_id: str,
    workspace_id: str,
    limit: int = 500,
    message_ids: list[str] | None = None,
    received_after: str | None = None,
) -> dict[str, int]:
    client = OAuthStorage().client
    rules = _rows(
        client.table("message_classification_rules")
        .select("*")
        .eq("account_id", account_id)
        .eq("workspace_id", workspace_id)
        .eq("is_active", True)
        .order("priority", desc=False)
        .order("created_at", desc=False)
        .execute()
    )
    if message_ids is not None and not message_ids:
        messages: list[dict[str, Any]] = []
    else:
        query = (
            client.table("communication_messages")
            .select("*")
            .eq("account_id", account_id)
            .eq("case_processed", False)
        )
        if message_ids is not None:
            query = query.in_("id", list(dict.fromkeys(message_ids)))
        if received_after:
            query = query.gte("received_at", received_after)
        messages = _rows(
            query.order("received_at", desc=True)
            .limit(min(max(limit, 1), 1000))
            .execute()
        )
    totals = {"rules": len(rules), "matched": 0, "updated": 0, "cases_created": 0, "cases_removed": 0}
    for message in messages:
        rule = next((item for item in rules if _rule_matches(item, message)), None)
        if not rule:
            continue
        totals["matched"] += 1
        applied = _apply_rule_to_message(
            client=client,
            rule=rule,
            message=message,
            workspace_id=workspace_id,
            account_id=account_id,
        )
        for key in ("updated", "cases_created", "cases_removed"):
            totals[key] += int(applied.get(key) or 0)
    return totals
