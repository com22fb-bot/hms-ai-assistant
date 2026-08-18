from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from app.services.classification_catalog import (
    identify_sender,
    is_marketing_local_part,
    SECURITY_NOTICE_TERMS,
)
from app.services.classification_catalog.matching import sender_email as _sender_email


CLASSIFIER_VERSION = "logistica1-triage-v4"

PROMOTIONAL_MARKERS = (
    "newsletter",
    "marketing@",
    "promotions@",
    "subscribe@",
    "premium-updates@",
    "feature-updates@",
    "jobs-listings@",
    "career-interests-",
    "jooble.org",
    "academia-mail.com",
    "mg.remote.co",
    "mg.flexjobs.com",
    "openart.ai",
    "mail.cursor.com",
    "offers@",
    "deals@",
)

AUTOMATED_MARKERS = (
    "no-reply",
    "noreply",
    "no_reply",
    "do-not-reply",
    "donotreply",
    "mailer-daemon",
    "notifications@",
    "updates@",
    "welcome@",
    "hello@",
    "em@em1.",
    "system@",
)

NOTICE_TERMS = (
    "payment was declined",
    "pago rechazado",
    "pago declinado",
    "project is going to be paused",
    "project will be paused",
    "proyecto será pausado",
    "proyecto se pausará",
    "account suspended",
    "cuenta suspendida",
    "security alert",
    "alerta de seguridad",
    "verify your email",
    "verifica tu correo",
    "confirm your email",
    "confirme la dirección de correo",
    "password reset",
    "contraseña restablecida",
    "invoice overdue",
    "factura vencida",
    "subscription expired",
    "suscripción vencida",
    "final notice",
    "último aviso",
    "action required",
    "acción requerida",
    "service interruption",
    "interrupción del servicio",
    "estado de cuenta",
    "statement is ready",
    "account statement",
    "cargo aprobado",
    "compra aprobada",
    "purchase approved",
    "pedido enviado",
    "order shipped",
    "order delivered",
    "paquete entregado",
    "out for delivery",
    "tracking number",
    "número de guía",
    "reservación confirmada",
    "reservation confirmed",
    "booking confirmed",
    "boarding pass",
    "pase de embarque",
    "check-in is open",
    "check in is open",
    "disponible el check-in",
    "spei",
    "wire transfer",
    "depósito recibido",
    "deposit received",
)

DIRECT_ACTION_TERMS = (
    "favor de enviar",
    "favor de confirmar",
    "favor de revisar",
    "por favor envía",
    "por favor envia",
    "por favor confirma",
    "por favor revisa",
    "please send",
    "please confirm",
    "please review",
    "se solicita",
    "solicito que",
    "necesitamos que",
    "requerimos que",
    "puedes enviar",
    "podrías enviar",
    "puedes confirmar",
    "podrías confirmar",
    "can you send",
    "could you send",
    "can you confirm",
    "could you confirm",
    "quedo atento",
    "quedamos atentos",
)

PAYMENT_ACTION_TERMS = (
    "pendiente pago",
    "pendiente de pago",
    "pago pendiente",
    "requerimos pagar",
    "necesitamos pagar",
    "debemos pagar",
    "se debe pagar",
    "hay que pagar",
    "pagar la mensualidad",
    "factura por pagar",
    "payment due",
    "payment pending",
    "we need to pay",
)


DEADLINE_TERMS = (
    "antes del",
    "a más tardar",
    "fecha límite",
    "deadline",
    "vence el",
    "vencimiento",
)

REMINDER_TERMS = (
    "recordatorio",
    "reminder",
    "seguimiento",
    "follow up",
    "follow-up",
    "segunda solicitud",
    "second request",
    "espero tu respuesta",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _message_direction(message: dict[str, Any]) -> str:
    labels = {str(item).upper() for item in (message.get("labels") or [])}
    if "DRAFT" in labels:
        return "draft"
    if "SENT" in labels and "INBOX" not in labels:
        return "outbound"
    if "INBOX" in labels:
        return "inbound"
    return str(message.get("direction") or "inbound")


def _text_has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _sender_is_promotional(sender: str) -> bool:
    normalized = sender.lower()
    return any(marker in normalized for marker in PROMOTIONAL_MARKERS)


def _sender_is_automated(sender: str) -> bool:
    normalized = sender.lower()
    return any(marker in normalized for marker in AUTOMATED_MARKERS)


def _classify_known_vertical(
    sender: str,
    short_text: str,
    existing_case: dict[str, Any] | None,
) -> tuple[str, int, str, bool] | None:
    identity = identify_sender(sender)
    if not identity:
        return None

    vertical = str(identity.get("vertical") or "")
    name = str(identity.get("name") or "remitente conocido")
    region = str(identity.get("region") or "")
    region_bit = f" ({region})" if region else ""

    if vertical == "social":
        if _text_has_any(short_text, SECURITY_NOTICE_TERMS):
            return (
                "notice",
                80,
                f"Seguridad de cuenta en {name}.",
                False,
            )
        return (
            "social",
            5,
            f"Red social: {name}. No genera un caso operativo.",
            False,
        )

    if vertical not in {"bank", "commerce", "travel"}:
        return None

    labels = {
        "bank": "banco",
        "commerce": "pedido o compra",
        "travel": "reservación o viaje",
    }
    kind = labels[vertical]
    marketing = is_marketing_local_part(sender)
    needs_action = _text_has_any(
        short_text,
        DIRECT_ACTION_TERMS + PAYMENT_ACTION_TERMS,
    )
    security_or_notice = _text_has_any(
        short_text,
        NOTICE_TERMS + SECURITY_NOTICE_TERMS,
    )

    if marketing and not needs_action and not security_or_notice:
        return (
            "promotional",
            5,
            f"Campaña comercial de {name}.",
            False,
        )
    if needs_action or existing_case is not None:
        return (
            "action_required",
            85,
            f"Hay un pago o trámite pendiente con {name}.",
            True,
        )
    return (
        "notice",
        70,
        f"Aviso de {kind}: {name}{region_bit}.",
        False,
    )


def classify_message(
    message: dict[str, Any],
    *,
    existing_case: dict[str, Any] | None,
) -> tuple[str, int, str, bool]:
    labels = {str(item).upper() for item in (message.get("labels") or [])}
    sender = str(message.get("sender") or "")
    subject = str(message.get("subject") or "")
    body = str(message.get("body_text") or message.get("snippet") or "")
    short_text = f"{subject}\n{body[:1600]}".lower()
    self_delivered = "SENT" in labels and "INBOX" in labels
    direction = _message_direction(message)

    if "DRAFT" in labels:
        return ("informational", 0, "Borrador excluido del flujo operativo.", False)
    if "SPAM" in labels or "TRASH" in labels:
        return ("informational", 0, "Mensaje excluido por su ubicación en el proveedor.", False)
    if direction == "outbound" and not self_delivered:
        if existing_case is not None:
            return ("waiting_external", 75, "Respuesta enviada dentro de un caso existente.", True)
        return ("informational", 15, "Mensaje enviado sin un caso abierto previo.", False)

    known = _classify_known_vertical(sender, short_text, existing_case)
    if known is not None:
        return known

    if _text_has_any(short_text, SECURITY_NOTICE_TERMS):
        return (
            "notice",
            80,
            "Aviso de seguridad o verificación de cuenta.",
            False,
        )
    if "CATEGORY_SOCIAL" in labels:
        return ("social", 5, "Mensaje de red social; no genera un caso operativo.", False)
    if "CATEGORY_PROMOTIONS" in labels or _sender_is_promotional(sender):
        return ("promotional", 5, "Publicidad, campaña, vacante masiva o boletín comercial.", False)
    if _text_has_any(short_text, NOTICE_TERMS):
        return ("notice", 70, "Aviso importante para revisión, sin convertirlo automáticamente en caso.", False)
    if "CATEGORY_FORUMS" in labels:
        return ("informational", 10, "Mensaje de foro o lista informativa.", False)
    if _sender_is_automated(sender):
        return ("automated", 10, "Remitente automatizado sin una solicitud humana directa.", False)
    if existing_case is not None:
        return ("action_required", 85, "Continuación de una conversación con un caso abierto.", True)

    score = 20
    reasons: list[str] = []
    if any(term in short_text for term in DIRECT_ACTION_TERMS):
        score += 55
        reasons.append("contiene una solicitud directa")
    if any(term in short_text for term in PAYMENT_ACTION_TERMS):
        score += 60
        reasons.append("contiene una obligación o pago pendiente")
    if any(term in short_text for term in DEADLINE_TERMS):
        score += 20
        reasons.append("incluye una fecha límite")
    if any(term in short_text for term in REMINDER_TERMS):
        score += 25
        reasons.append("es un seguimiento o recordatorio")
    if "?" in subject and reasons:
        score += 10
        reasons.append("el asunto contiene una pregunta")
    if bool(message.get("is_unread")):
        score += 5
    score = min(score, 100)

    if score >= 70 and reasons:
        prefix = "Nota enviada a la misma cuenta: " if self_delivered else "Se detectó que "
        return ("action_required", score, prefix + ", ".join(reasons) + ".", True)
    if "CATEGORY_PERSONAL" in labels or _sender_email(sender) or self_delivered:
        return ("review", max(score, 30), "Mensaje personal sin una solicitud suficientemente clara; requiere revisión humana.", False)
    return ("informational", score, "No se detectó una solicitud operativa clara.", False)


def _mark_without_case(
    *,
    client: Any,
    message: dict[str, Any],
    category: str,
    score: int,
    reason: str,
) -> None:
    from app.services.case_engine import normalize_subject

    subject = str(message.get("subject") or "")
    direction = _message_direction(message)
    now = _now_iso()

    (
        client.table("communication_messages")
        .update(
            {
                "normalized_subject": normalize_subject(subject),
                "direction": direction,
                "case_processed": True,
                "processed_at": now,
                "triage_category": category,
                "actionability_score": score,
                "triage_reason": reason,
                "triaged_at": now,
            }
        )
        .eq("id", str(message["id"]))
        .execute()
    )


def classify_pending_messages(
    *,
    account_id: str,
    workspace_id: str,
    limit: int = 100,
    message_ids: list[str] | None = None,
    received_after: str | None = None,
) -> dict[str, Any]:
    from app.services.case_engine import (
        _find_case_for_message,
        _rows,
        normalize_subject,
        process_message,
    )
    from app.services.oauth_storage import OAuthStorage

    storage = OAuthStorage()
    account = storage.get_account(account_id)

    if not account:
        raise RuntimeError("La cuenta de correo ya no existe.")

    if str(account.get("workspace_id") or "") != workspace_id:
        raise RuntimeError(
            "La cuenta no pertenece al workspace del trabajo."
        )

    client = storage.client
    safe_limit = min(max(limit, 1), 500)

    if message_ids is not None and not message_ids:
        messages: list[dict[str, Any]] = []
    else:
        query = (
            client.table("communication_messages")
            .select(
                "id,thread_id,account_id,external_message_id,sender,"
                "recipients,cc,bcc,subject,body_text,snippet,"
                "received_at,labels,is_unread,direction,case_processed"
            )
            .eq("account_id", account_id)
            .eq("case_processed", False)
        )
        if message_ids is not None:
            query = query.in_("id", list(dict.fromkeys(message_ids)))
        if received_after:
            query = query.gte("received_at", received_after)
        response = query.order("received_at", desc=True).limit(safe_limit).execute()
        messages = _rows(response)
    processed = 0
    created_cases = 0
    linked_cases = 0
    without_case = 0
    errors = 0
    categories: Counter[str] = Counter()
    error_details: list[dict[str, str]] = []

    for message in messages:
        try:
            normalized_subject = normalize_subject(
                str(message.get("subject") or "")
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
            category, score, reason, actionable = classify_message(
                message,
                existing_case=existing_case,
            )

            if actionable:
                _, result = process_message(
                    client=client,
                    workspace_id=workspace_id,
                    account_id=account_id,
                    message=message,
                )
                (
                    client.table("communication_messages")
                    .update(
                        {
                            "triage_category": category,
                            "actionability_score": score,
                            "triage_reason": reason,
                            "triaged_at": _now_iso(),
                        }
                    )
                    .eq("id", str(message["id"]))
                    .execute()
                )
                if result == "created":
                    created_cases += 1
                else:
                    linked_cases += 1
            else:
                _mark_without_case(
                    client=client,
                    message=message,
                    category=category,
                    score=score,
                    reason=reason,
                )
                without_case += 1

            categories[category] += 1
            processed += 1

        except Exception as error:
            errors += 1
            error_text = str(error)[:1200]
            now = _now_iso()

            # Un error aislado no debe detener ni repetir infinitamente
            # toda la reclasificación. El mensaje queda en revisión humana.
            (
                client.table("communication_messages")
                .update(
                    {
                        "case_processed": True,
                        "processed_at": now,
                        "triage_category": "review",
                        "actionability_score": 0,
                        "triage_reason": (
                            "Revisión necesaria por incidencia técnica: "
                            + error_text
                        ),
                        "triaged_at": now,
                    }
                )
                .eq("id", str(message.get("id") or ""))
                .execute()
            )
            categories["review"] += 1
            without_case += 1
            processed += 1

            if len(error_details) < 20:
                error_details.append(
                    {
                        "message_id": str(
                            message.get("id") or ""
                        ),
                        "error": error_text,
                    }
                )

    return {
        "status": "ok" if errors == 0 else "partial",
        "classifier_version": CLASSIFIER_VERSION,
        "found": len(messages),
        "processed": processed,
        "created_cases": created_cases,
        "linked_cases": linked_cases,
        "without_case": without_case,
        "errors": errors,
        "categories": dict(categories),
        "error_details": error_details,
    }
