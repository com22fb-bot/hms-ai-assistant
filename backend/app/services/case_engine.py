from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from email.utils import getaddresses
from typing import Any

from fastapi import HTTPException

from app.services.mail_direction import direction_from_labels
from app.services.event_engine import create_case_event
from app.services.learning_engine import register_pattern
from app.security.identity import require_google_account
from app.services.oauth_storage import OAuthStorage
from app.utils.html_text import strip_css_noise


_INFORMATIVE_TRIAGE = frozenset({"informational", "notice", "review", "automated"})

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


# --- Agrupación por evento (catalogo-maestro.yaml · agrupacion) -------------
import re as _re
from datetime import timedelta as _td

_SECURITY_RE = _re.compile(
    r"(alerta de seguridad|security alert|nuevo inicio de sesi[oó]n|new sign-?in|"
    r"nuevo dispositivo|new device|actividad (inusual|sospechosa)|unusual activity|"
    r"suspicious (activity|sign)|alerte de s[eé]curit[eé]|avviso di sicurezza|alerta de seguran[cç]a|"
    r"contrase[nñ]a (se ha )?(cambiado|actualizado)|password (changed|was changed|reset))",
    _re.I,
)
_CODE_RE = _re.compile(
    r"(c[oó]digo de (verificaci[oó]n|seguridad|acceso)|verification code|security code|"
    r"one[- ]time (pass(word|code)|code)|\botp\b|es tu c[oó]digo|is your .{0,30}code|"
    r"code de v[eé]rification|codice di verifica|c[oó]digo de verifica[cç][aã]o)",
    _re.I,
)
_CODE_DIGITS = _re.compile(r"(?<![\d-])\d{4,8}(?![\d-])")
_GENERIC_LABELS = {"mail", "email", "accounts", "account", "noreply", "no-reply", "info",
                   "notifications", "notification", "alerts", "news", "em", "e", "m", "mg", "www"}
_SECOND_LEVEL = {"com", "co", "net", "org", "gob", "gov", "edu", "ac"}
EVENT_WINDOW_DAYS = {"security_alert": 7, "verification_code": 1}


def brand_of_email(email: str | None) -> str:
    """accounts.google.com / noreply@google.com -> google; e.bbva.mx -> bbva."""
    domain = str(email or "").split("@")[-1].strip().lower().strip(">")
    labels = [part for part in domain.split(".") if part]
    if len(labels) > 1:
        labels.pop()
    if len(labels) > 1 and labels[-1] in _SECOND_LEVEL:
        labels.pop()
    while labels and labels[-1] in _GENERIC_LABELS:
        labels.pop()
    return labels[-1] if labels else ""


def event_topic(text: str) -> str | None:
    if _CODE_RE.search(text or ""):
        return "verification_code"
    if _SECURITY_RE.search(text or ""):
        return "security_alert"
    return None


def event_key_for(sender_email: str | None, text: str) -> tuple[str, int] | None:
    """Clave de evento por usuario: marca + tema. Ventana en días."""
    topic = event_topic(text)
    brand = brand_of_email(sender_email)
    if not topic or not brand:
        return None
    return f"{brand}:{topic}", EVENT_WINDOW_DAYS[topic]


def mask_codes(text: str | None) -> str | None:
    """Nunca mostrar códigos de verificación (decisión 2)."""
    if text is None:
        return None
    return _CODE_DIGITS.sub("••••••", text)


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


def _brain_v1_on() -> bool:
    from app.services.brain_v1 import brain_v1_enabled

    return brain_v1_enabled()


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

    if _brain_v1_on():
        # C4: "Recordatorio: Factura X" y "Factura X" son el mismo asunto.
        notice_prefix = re.compile(
            r"^(?:(?:re|fw|fwd|rv|enc|aw|wg|recordatorio|reminder|aviso|[uú]ltimo aviso|"
            r"segundo aviso|final notice|friendly reminder)\s*:\s*)+",
            flags=re.IGNORECASE,
        )
        previous = None
        while value != previous:
            previous = value
            value = notice_prefix.sub("", value).strip()

    value = re.sub(r"\[[^\]]{1,30}\]", " ", value)
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"[^\wáéíóúüñ@#\-/ ]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()

    return value[:500]


def _message_direction(message: dict[str, Any]) -> str:
    return direction_from_labels(message.get("labels"), message.get("direction"))


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
    workspace_id: str | None = None,
    event_key: str | None = None,
    received_at: str | None = None,
    window_days: int = 7,
    reply_ids: list[str] | None = None,
    sender_email: str | None = None,
    evidence_text: str | None = None,
) -> dict[str, Any] | None:
    """Busca el caso abierto del mismo evento.

    Alcance: el usuario (workspace, todos sus buzones), no solo el buzón.
    Orden (P0.2, issue #195): mismo hilo del buzón → In-Reply-To/References
    → misma clave de evento (marca+tema) dentro de la ventana → mismo asunto
    normalizado SOLO con evidencia corroborante (mismo remitente que el
    solicitante del caso y un identificador común: folio/referencia/importe).
    El asunto normalizado por sí solo nunca basta; sin evidencia no se asocia.
    """
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

    if reply_ids:
        found = _find_case_by_reply_ids(
            client=client,
            account_id=account_id,
            reply_ids=reply_ids,
            workspace_id=workspace_id,
        )
        if found:
            return found

    scope_column, scope_value = (
        ("workspace_id", workspace_id) if workspace_id else ("account_id", account_id)
    )

    if event_key:
        query = (
            client.table("intelligent_cases")
            .select("*")
            .eq(scope_column, scope_value)
            .eq("metadata->>event_key", event_key)
            .in_("status", _OPEN_STATUSES)
        )
        if received_at:
            try:
                anchor = datetime.fromisoformat(str(received_at).replace("Z", "+00:00"))
                query = query.gte(
                    "last_activity_at", (anchor - _td(days=window_days)).isoformat()
                )
            except ValueError:
                pass
        found = _first_row(
            query.order("last_activity_at", desc=True).limit(1).execute()
        )
        if found:
            return found

    if normalized_subject and sender_email and evidence_text:
        candidates = _rows(
            client.table("intelligent_cases")
            .select("*")
            .eq(scope_column, scope_value)
            .eq("normalized_subject", normalized_subject)
            .in_("status", _OPEN_STATUSES)
            .order("last_activity_at", desc=True)
            .limit(20)
            .execute()
        )
        for candidate in candidates:
            if _has_corroborating_evidence(candidate, sender_email, evidence_text):
                return candidate

    return None


_IDENTIFIER_RE = re.compile(r"\b(?:[a-z]{1,6}[-#]?)?\d{5,}\b", re.IGNORECASE)
_AMOUNT_RE = re.compile(r"\$\s?(\d[\d,]*\.\d{2})")


def _identifiers(text: str | None) -> set[str]:
    value = str(text or "").lower()
    ids = {m.group(0).replace("#", "").replace("-", "") for m in _IDENTIFIER_RE.finditer(value)}
    ids |= {
        "$" + m.group(1).replace(",", "")
        for m in _AMOUNT_RE.finditer(value)
        if m.group(1).replace(",", "") not in {"0.00"}
    }
    return ids


def _has_corroborating_evidence(
    case: dict[str, Any], sender_email: str, evidence_text: str
) -> bool:
    """Evidencia mínima para asociar por asunto sin hilo (P0.2)."""
    requester = str(case.get("requester_email") or "").strip().lower()
    if not requester or requester != str(sender_email or "").strip().lower():
        return False
    case_ids = _identifiers(f"{case.get('title') or ''}\n{case.get('summary') or ''}")
    return bool(case_ids & _identifiers(evidence_text))


def _find_case_by_reply_ids(
    *,
    client: Any,
    account_id: str,
    reply_ids: list[str],
    workspace_id: str | None = None,
) -> dict[str, Any] | None:
    """Caso abierto referenciado por In-Reply-To/References.

    Aislamiento (P0, issue #195): mismo criterio que _find_case_for_message.
    Con workspace_id solo casos de ese workspace; sin él, solo de la cuenta.
    Además se comprueba el alcance de la fila devuelta (defensa en profundidad):
    no se confía en que case_messages apunte a un caso del mismo alcance.
    """
    scope_column, scope_value = (
        ("workspace_id", workspace_id) if workspace_id else ("account_id", account_id)
    )
    wanted = [str(item).strip() for item in reply_ids if str(item or "").strip()]
    if not wanted:
        return None
    variants = sorted({v for item in wanted for v in (item, item.strip("<>"), f"<{item.strip('<>')}>")})
    parents = _rows(
        client.table("communication_messages")
        .select("id")
        .eq("account_id", account_id)
        .in_("internet_message_id", variants)
        .execute()
    )
    parent_ids = [str(row["id"]) for row in parents if row.get("id")]
    if not parent_ids:
        return None
    links = _rows(
        client.table("case_messages")
        .select("case_id")
        .in_("message_id", parent_ids)
        .execute()
    )
    case_ids = list(dict.fromkeys(str(row["case_id"]) for row in links if row.get("case_id")))
    if not case_ids:
        return None
    found = _first_row(
        client.table("intelligent_cases")
        .select("*")
        .eq(scope_column, scope_value)
        .in_("id", case_ids)
        .in_("status", _OPEN_STATUSES)
        .order("last_activity_at", desc=True)
        .limit(1)
        .execute()
    )
    if not found or str(found.get(scope_column) or "") != str(scope_value or ""):
        return None
    if found.get("status") not in _OPEN_STATUSES:
        return None
    return found


def message_reply_ids(message: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    if message.get("in_reply_to"):
        ids.append(str(message["in_reply_to"]))
    refs = message.get("references_header") or []
    if isinstance(refs, str):
        refs = refs.split()
    ids.extend(str(item) for item in refs if item)
    return ids


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
    triage_category: str | None = None,
) -> tuple[str, str]:
    message_id = str(message["id"])
    received_at = _to_iso(message.get("received_at"))
    subject = strip_css_noise(str(message.get("subject") or "")) or "(Sin asunto)"
    body = str(message.get("body_text") or message.get("snippet") or "")
    if "{" in body:
        body = strip_css_noise(body)
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

    event = event_key_for(sender_email, text)
    event_key = event[0] if event else None
    is_code = bool(event_key and event_key.endswith(":verification_code"))
    if is_code:
        subject = mask_codes(subject) or subject
        body = mask_codes(body) or body
        text = f"{subject}\n{body}"
        normalized_subject = normalize_subject(subject)

    existing_case = _find_case_for_message(
        client=client,
        account_id=account_id,
        thread_id=(
            str(message.get("thread_id"))
            if message.get("thread_id")
            else None
        ),
        normalized_subject=normalized_subject,
        workspace_id=workspace_id,
        event_key=event_key,
        received_at=received_at,
        window_days=event[1] if event else 7,
        reply_ids=message_reply_ids(message),
        sender_email=sender_email,
        evidence_text=text,
    )

    created = existing_case is None

    if created:
        risk, priority, level = _risk_and_priority(
            text=text,
            is_unread=bool(message.get("is_unread")),
            reminder_count=1 if is_reminder else 0,
        )
        if is_code:
            # Código de verificación = "Cuando puedas"; nunca urgente.
            priority, level = "low", 1

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
                        (
                            mask_codes(
                                (strip_css_noise(str(message.get("snippet") or "")) or body)[:500]
                            )
                            if is_code
                            else (strip_css_noise(str(message.get("snippet") or "")) or body)[:500]
                        )
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
                        **({"event_key": event_key} if event_key else {}),
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
                "low"
                if is_code
                else priority
                if priority in ("high", "critical")
                else case.get("priority") or priority
            ),
        }

        # P0.2: un mensaje informativo vinculado (recibo, cancelación, aviso)
        # es evidencia; no cambia de quién se espera la acción.
        if triage_category in _INFORMATIVE_TRIAGE:
            pass
        elif direction == "outbound":
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
