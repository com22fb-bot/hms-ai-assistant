from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from email.utils import getaddresses
from typing import Any

from fastapi import HTTPException

from app.services.event_engine import create_case_event
from app.services.learning_engine import register_pattern
from app.security.identity import require_google_account
from app.services.oauth_storage import OAuthStorage


_OPEN_STATUSES = [
    "new",
    "analyzing",
    "in_progress",
    "delegated",
    "waiting_internal",
    "waiting_external",
]

_REMINDER_TERMS = (
    "recordatorio",
    "reminder",
    "seguimiento",
    "follow up",
    "follow-up",
    "segunda solicitud",
    "second request",
    "urgente",
    "urgent",
)

_CRITICAL_TERMS = (
    "legal",
    "demanda",
    "lawsuit",
    "fraude",
    "fraud",
    "suspensión",
    "suspension",
    "vencido",
    "overdue",
    "último aviso",
    "final notice",
)

_REQUEST_TERMS = (
    "favor de",
    "por favor",
    "please",
    "se solicita",
    "necesitamos",
    "need",
    "required",
    "requerimos",
    "quedo atento",
    "confirmar",
    "confirm",
    "enviar",
    "send",
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(value: datetime | str | None) -> str:
    if isinstance(value, str) and value:
        return value

    if isinstance(value, datetime):
        current = value
    else:
        current = _utc_now()

    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)

    return current.astimezone(timezone.utc).isoformat()


def _rows(response: Any) -> list[dict[str, Any]]:
    data = getattr(response, "data", None)

    if isinstance(data, list):
        return [
            item
            for item in data
            if isinstance(item, dict)
        ]

    if isinstance(data, dict):
        return [data]

    return []


def _first_row(response: Any) -> dict[str, Any] | None:
    rows = _rows(response)
    return rows[0] if rows else None


def normalize_subject(subject: str | None) -> str:
    value = (subject or "").strip().lower()

    prefix_pattern = re.compile(
        r"^(?:(?:re|fw|fwd|rv|enc|aw|wg)\s*:\s*)+",
        flags=re.IGNORECASE,
    )

    previous = None

    while value != previous:
        previous = value
        value = prefix_pattern.sub("", value).strip()

    value = re.sub(r"\[[^\]]{1,30}\]", " ", value)
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"[^\wáéíóúüñ@#\-/ ]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()

    return value[:500]


def _message_direction(message: dict[str, Any]) -> str:
    labels = {
        str(item).upper()
        for item in (message.get("labels") or [])
    }

    if "SENT" in labels:
        return "outbound"

    if "DRAFT" in labels:
        return "draft"

    return str(message.get("direction") or "inbound")


def _sender_parts(sender: str | None) -> tuple[str | None, str | None]:
    values = getaddresses([sender or ""])

    if not values:
        return None, None

    name, email = values[0]

    return (
        name.strip() or None,
        email.strip().lower() or None,
    )


def _recipient_emails(message: dict[str, Any]) -> list[str]:
    result: list[str] = []

    for field in ("recipients", "cc", "bcc"):
        for item in message.get(field) or []:
            if not isinstance(item, dict):
                continue

            email = str(item.get("email") or "").strip().lower()

            if email:
                result.append(email)

    return list(dict.fromkeys(result))


def _classify_case_type(text: str) -> str:
    normalized = text.lower()

    categories = {
        "invoice": (
            "factura",
            "invoice",
            "cfdi",
            "billing",
        ),
        "payment": (
            "pago",
            "payment",
            "transferencia",
            "deposit",
            "cobro",
        ),
        "quotation": (
            "cotización",
            "cotizacion",
            "quotation",
            "quote",
            "estimate",
        ),
        "meeting": (
            "reunión",
            "reunion",
            "meeting",
            "calendar",
            "cita",
        ),
        "document": (
            "documento",
            "document",
            "archivo",
            "file",
            "contrato",
            "contract",
        ),
        "support": (
            "error",
            "falla",
            "incident",
            "incidencia",
            "support",
            "soporte",
        ),
    }

    for case_type, terms in categories.items():
        if any(term in normalized for term in terms):
            return case_type

    return "general"


def _requested_action(text: str) -> str | None:
    normalized = " ".join(text.split())

    for term in _REQUEST_TERMS:
        position = normalized.lower().find(term)

        if position >= 0:
            return normalized[position:position + 350]

    return None


def _risk_and_priority(
    *,
    text: str,
    is_unread: bool,
    reminder_count: int,
) -> tuple[int, str, int]:
    normalized = text.lower()
    risk = 20
    event_level = 1

    if is_unread:
        risk += 8

    if any(term in normalized for term in _REQUEST_TERMS):
        risk += 12

    if any(term in normalized for term in _REMINDER_TERMS):
        risk += 18
        event_level = 2

    if any(term in normalized for term in _CRITICAL_TERMS):
        risk += 35
        event_level = 4

    risk += min(reminder_count * 12, 30)
    risk = min(risk, 100)

    if risk >= 80:
        priority = "critical"
    elif risk >= 55:
        priority = "high"
    elif risk <= 20:
        priority = "low"
    else:
        priority = "normal"

    return risk, priority, event_level


def _active_context() -> tuple[OAuthStorage, dict[str, Any]]:
    _, account = require_google_account()
    return OAuthStorage(), account


def _find_case_for_message(
    *,
    client: Any,
    account_id: str,
    thread_id: str | None,
    normalized_subject: str,
) -> dict[str, Any] | None:
    if thread_id:
        response = (
            client.table("intelligent_cases")
            .select("*")
            .eq("account_id", account_id)
            .eq("primary_thread_id", thread_id)
            .in_("status", _OPEN_STATUSES)
            .order("last_activity_at", desc=True)
            .limit(1)
            .execute()
        )

        found = _first_row(response)

        if found:
            return found

    if normalized_subject:
        response = (
            client.table("intelligent_cases")
            .select("*")
            .eq("account_id", account_id)
            .eq("normalized_subject", normalized_subject)
            .in_("status", _OPEN_STATUSES)
            .order("last_activity_at", desc=True)
            .limit(1)
            .execute()
        )

        found = _first_row(response)

        if found:
            return found

    return None


def _upsert_participant(
    *,
    client: Any,
    case_id: str,
    email: str,
    display_name: str | None,
    participant_role: str,
    seen_at: str,
) -> None:
    normalized_email = email.strip().lower()

    if not normalized_email:
        return

    response = (
        client.table("case_participants")
        .select("*")
        .eq("case_id", case_id)
        .eq("email", normalized_email)
        .limit(1)
        .execute()
    )

    existing = _first_row(response)

    if not existing:
        (
            client.table("case_participants")
            .insert(
                {
                    "case_id": case_id,
                    "email": normalized_email,
                    "display_name": display_name,
                    "participant_role": participant_role,
                    "message_count": 1,
                    "first_seen_at": seen_at,
                    "last_seen_at": seen_at,
                }
            )
            .execute()
        )
        return

    (
        client.table("case_participants")
        .update(
            {
                "display_name": (
                    display_name
                    or existing.get("display_name")
                ),
                "participant_role": (
                    participant_role
                    if participant_role != "participant"
                    else existing.get("participant_role")
                ),
                "message_count": int(
                    existing.get("message_count") or 0
                ) + 1,
                "last_seen_at": seen_at,
            }
        )
        .eq("id", existing["id"])
        .execute()
    )


def _update_learning(
    *,
    client: Any,
    workspace_id: str,
    case_type: str,
    requester_email: str | None,
    recipient_emails: list[str],
) -> None:
    if requester_email and "@" in requester_email:
        domain = requester_email.split("@", 1)[1]

        register_pattern(
            client=client,
            workspace_id=workspace_id,
            pattern_type="requester_domain_case_type",
            pattern_key=f"{domain}:{case_type}",
            pattern_value={
                "requester_domain": domain,
                "case_type": case_type,
            },
        )

    for recipient in recipient_emails:
        register_pattern(
            client=client,
            workspace_id=workspace_id,
            pattern_type="case_routing",
            pattern_key=f"{case_type}:{recipient}",
            pattern_value={
                "case_type": case_type,
                "usual_recipient": recipient,
            },
        )


def process_message(
    *,
    client: Any,
    workspace_id: str,
    account_id: str,
    message: dict[str, Any],
) -> tuple[str, str]:
    message_id = str(message["id"])
    received_at = _to_iso(message.get("received_at"))
    subject = str(message.get("subject") or "(Sin asunto)")
    body = str(message.get("body_text") or message.get("snippet") or "")
    normalized_subject = normalize_subject(subject)
    direction = _message_direction(message)
    sender_name, sender_email = _sender_parts(message.get("sender"))
    recipient_emails = _recipient_emails(message)
    text = f"{subject}\n{body}"
    case_type = _classify_case_type(text)
    is_reminder = any(
        term in text.lower()
        for term in _REMINDER_TERMS
    )

    existing_case = _find_case_for_message(
        client=client,
        account_id=account_id,
        thread_id=(
            str(message.get("thread_id"))
            if message.get("thread_id")
            else None
        ),
        normalized_subject=normalized_subject,
    )

    created = existing_case is None

    if created:
        risk, priority, level = _risk_and_priority(
            text=text,
            is_unread=bool(message.get("is_unread")),
            reminder_count=1 if is_reminder else 0,
        )

        requester_email = (
            sender_email
            if direction == "inbound"
            else None
        )

        response = (
            client.table("intelligent_cases")
            .insert(
                {
                    "workspace_id": workspace_id,
                    "account_id": account_id,
                    "primary_thread_id": message.get("thread_id"),
                    "title": subject,
                    "normalized_subject": normalized_subject,
                    "case_type": case_type,
                    "status": "new",
                    "priority": priority,
                    "risk_score": risk,
                    "confidence": 0.7000,
                    "summary": (
                        str(message.get("snippet") or body)[:500]
                        or None
                    ),
                    "requested_action": _requested_action(text),
                    "requester_name": (
                        sender_name
                        if direction == "inbound"
                        else None
                    ),
                    "requester_email": requester_email,
                    "waiting_on": (
                        "internal"
                        if direction == "inbound"
                        else "external"
                    ),
                    "opened_at": received_at,
                    "last_activity_at": received_at,
                    "source_count": 1,
                    "reminder_count": 1 if is_reminder else 0,
                    "metadata": {
                        "created_by": "case_engine_v1",
                        "initial_message_direction": direction,
                    },
                }
            )
            .execute()
        )

        case = _first_row(response)

        if not case:
            raise RuntimeError(
                "Supabase no confirmó la creación del caso."
            )

        create_case_event(
            client=client,
            workspace_id=workspace_id,
            case_id=str(case["id"]),
            message_id=message_id,
            event_type="case_created",
            level=max(level, 2),
            title="Nuevo caso detectado",
            description=subject,
            dedupe_key=f"case_created:{message_id}",
            metadata={
                "direction": direction,
                "case_type": case_type,
            },
        )

    else:
        case = existing_case
        reminder_count = int(
            case.get("reminder_count") or 0
        ) + (1 if is_reminder else 0)

        risk, priority, level = _risk_and_priority(
            text=text,
            is_unread=bool(message.get("is_unread")),
            reminder_count=reminder_count,
        )

        updates: dict[str, Any] = {
            "last_activity_at": received_at,
            "source_count": int(
                case.get("source_count") or 0
            ) + 1,
            "reminder_count": reminder_count,
            "risk_score": max(
                int(case.get("risk_score") or 0),
                risk,
            ),
            "priority": (
                priority
                if priority in ("high", "critical")
                else case.get("priority") or priority
            ),
        }

        if direction == "outbound":
            updates["waiting_on"] = "external"
        elif direction == "inbound":
            updates["waiting_on"] = "internal"

        (
            client.table("intelligent_cases")
            .update(updates)
            .eq("id", case["id"])
            .execute()
        )

        if is_reminder:
            event_type = "reminder_received"
            event_title = "Recordatorio recibido"
            event_description = (
                "El solicitante reiteró la solicitud. "
                "El caso continúa abierto."
            )
            event_level = max(level, 2)
        elif direction == "outbound":
            event_type = "outbound_message"
            event_title = "Respuesta o delegación enviada"
            event_description = (
                "Se detectó un mensaje enviado. "
                "Esto no cierra automáticamente el caso."
            )
            event_level = 1
        else:
            event_type = "external_reply"
            event_title = "Nueva evidencia recibida"
            event_description = (
                "Se agregó una respuesta al caso."
            )
            event_level = level

        create_case_event(
            client=client,
            workspace_id=workspace_id,
            case_id=str(case["id"]),
            message_id=message_id,
            event_type=event_type,
            level=event_level,
            title=event_title,
            description=event_description,
            dedupe_key=f"{event_type}:{message_id}",
            metadata={
                "direction": direction,
                "is_reminder": is_reminder,
            },
        )

    case_id = str(case["id"])

    (
        client.table("case_messages")
        .insert(
            {
                "case_id": case_id,
                "message_id": message_id,
                "relation_type": "evidence",
                "is_primary": created,
                "linked_at": received_at,
            }
        )
        .execute()
    )

    if sender_email:
        _upsert_participant(
            client=client,
            case_id=case_id,
            email=sender_email,
            display_name=sender_name,
            participant_role=(
                "requester"
                if direction == "inbound"
                else "sender"
            ),
            seen_at=received_at,
        )

    for recipient in recipient_emails:
        _upsert_participant(
            client=client,
            case_id=case_id,
            email=recipient,
            display_name=None,
            participant_role="recipient",
            seen_at=received_at,
        )

    _update_learning(
        client=client,
        workspace_id=workspace_id,
        case_type=case_type,
        requester_email=sender_email,
        recipient_emails=recipient_emails,
    )

    (
        client.table("communication_messages")
        .update(
            {
                "normalized_subject": normalized_subject,
                "direction": direction,
                "correlation_key": (
                    f"thread:{message.get('thread_id')}"
                    if message.get("thread_id")
                    else f"subject:{normalized_subject}"
                ),
                "case_processed": True,
                "processed_at": _to_iso(None),
            }
        )
        .eq("id", message_id)
        .execute()
    )

    return case_id, "created" if created else "linked"


def process_pending_messages(
    *,
    limit: int = 200,
    account_id: str | None = None,
    workspace_id: str | None = None,
) -> dict[str, Any]:
    enabled = os.getenv(
        "HMS_CASE_ENGINE_ENABLED",
        "false",
    ).strip().lower() in {"1", "true", "yes", "on"}

    if not enabled:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "maintenance",
                "message": (
                    "El clasificador de casos está temporalmente "
                    "detenido para evitar nuevos falsos positivos."
                ),
            },
        )

    if account_id is None:
        storage, account = _active_context()
        account_id = str(account["id"])
        workspace_id = str(account["workspace_id"])
    else:
        storage = OAuthStorage()
        account = storage.get_account(account_id)
        if not account:
            raise HTTPException(
                status_code=404,
                detail={
                    "status": "error",
                    "message": "La cuenta de procesamiento no existe.",
                },
            )
        account_workspace = str(account.get("workspace_id") or "")
        if workspace_id is not None and account_workspace != workspace_id:
            raise HTTPException(
                status_code=403,
                detail={
                    "status": "forbidden",
                    "message": "La cuenta no pertenece al workspace indicado.",
                },
            )
        workspace_id = account_workspace

    client = storage.client
    safe_limit = min(max(limit, 1), 500)

    response = (
        client.table("communication_messages")
        .select(
            "id,thread_id,account_id,external_message_id,sender,"
            "recipients,cc,bcc,subject,body_text,snippet,"
            "received_at,labels,is_unread,direction,case_processed"
        )
        .eq("account_id", account_id)
        .eq("case_processed", False)
        .order("received_at")
        .limit(safe_limit)
        .execute()
    )

    messages = _rows(response)
    processed = 0
    created_cases = 0
    linked_to_existing = 0
    errors = 0
    error_details: list[dict[str, str]] = []

    for message in messages:
        try:
            _, result = process_message(
                client=client,
                workspace_id=workspace_id,
                account_id=account_id,
                message=message,
            )

            processed += 1

            if result == "created":
                created_cases += 1
            else:
                linked_to_existing += 1

        except Exception as error:
            errors += 1

            if len(error_details) < 20:
                error_details.append(
                    {
                        "message_id": str(
                            message.get("id") or ""
                        ),
                        "error": str(error),
                    }
                )

    return {
        "status": "ok" if errors == 0 else "partial",
        "account_id": account_id,
        "requested_limit": safe_limit,
        "found": len(messages),
        "processed": processed,
        "created_cases": created_cases,
        "linked_to_existing": linked_to_existing,
        "errors": errors,
        "error_details": error_details,
    }
