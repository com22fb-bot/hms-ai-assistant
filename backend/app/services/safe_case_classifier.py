from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.mail_direction import (
    direction_from_labels,
    is_self_delivered,
    normalize_address,
    own_address_set,
)
import re
from app.services.classification_catalog import (
    identify_sender,
    is_marketing_local_part,
    SECURITY_NOTICE_TERMS,
)
from app.services.classification_catalog.matching import sender_email as _sender_email


CLASSIFIER_VERSION = "logistica1-triage-v5"

# P0.1 (issue #195): alertas de seguridad que REQUIEREN acción del usuario.
# Se evalúan antes que cualquier regla informativa. Frases condicionales como
# "si fuiste tú, no necesitas hacer nada" NO cuentan: solo la pregunta directa.
SECURITY_ACTION_PATTERNS = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"¿\s*fuiste\s+t[uú]\s*\?",
        r"\bwas\s+(?:this|it)\s+you\s*\?",
        r"\bconfirm(?:a|e|ar)?\s+(?:la\s+)?actividad\b",
        r"\bconfirm(?:a|e|ar)?\s+que\s+fuiste\s+t[uú]\b",
        r"\bconfirm\s+(?:the\s+)?activity\b",
        r"\bconfirm\s+it\s+was\s+you\b",
        r"\bactividad\s+sospechosa\b",
        r"\bsuspicious\s+(?:activity|sign[- ]?in|login)\b",
        r"\binicio\s+de\s+sesi[oó]n\s+sospechoso\b",
        r"\bintento\s+de\s+inicio\s+de\s+sesi[oó]n\s+(?:sospechoso|bloqueado)\b",
        r"\bbloqueamos\s+un\s+intento\b",
        r"\bblocked\s+(?:a\s+)?(?:suspicious\s+)?sign[- ]?in\s+attempt\b",
        r"\bcritical\s+security\s+alert\b",
        r"\balerta\s+de\s+seguridad\s+cr[ií]tica\b",
    )
)

# P0.2 (issue #195): mensajes que, aun relacionados con un caso abierto, son
# informativos (no crean acción pendiente ni cierran el caso por sí solos).
INFORMATIONAL_UPDATE_TERMS = (
    "pago recibido", "pago realizado", "pago exitoso", "pago aplicado",
    "hemos recibido tu pago", "recibimos tu pago", "tu pago fue recibido",
    "payment received", "payment successful", "thank you for your payment",
    "pagada", "pagado", "saldo $0", "saldo: $0", "comprobante de pago", "recibo de pago",
    "cancelación confirmada", "cancelacion confirmada", "fue cancelada", "fue cancelado",
    "ha sido cancelada", "ha sido cancelado", "subscription cancelled", "subscription canceled",
    "has been cancelled", "has been canceled",
)


def requires_security_action(text: str) -> bool:
    return any(p.search(text) for p in SECURITY_ACTION_PATTERNS)

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
    return direction_from_labels(message.get("labels"), message.get("direction"))


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
    if needs_action:
        return (
            "action_required",
            85,
            f"Hay un pago o trámite pendiente con {name}.",
            True,
        )
    if existing_case is not None:
        # P0.2: el caso abierto determina la vinculación, no la clasificación.
        return (
            "notice",
            70,
            f"Aviso de {kind} vinculado a un caso abierto con {name}.",
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
    own_addresses: set[str] | None = None,
) -> tuple[str, int, str, bool]:
    labels = {str(item).upper() for item in (message.get("labels") or [])}
    sender = str(message.get("sender") or "")
    subject = str(message.get("subject") or "")
    body = str(message.get("body_text") or message.get("snippet") or "")
    short_text = f"{subject}\n{body[:1600]}".lower()
    self_delivered = is_self_delivered(labels)
    direction = _message_direction(message)

    if "DRAFT" in labels:
        return ("informational", 0, "Borrador excluido del flujo operativo.", False)
    if "SPAM" in labels or "TRASH" in labels:
        return ("informational", 0, "Mensaje excluido por su ubicación en el proveedor.", False)
    if direction == "outbound" and not self_delivered:
        if existing_case is not None:
            return ("waiting_external", 75, "Respuesta enviada dentro de un caso existente.", True)
        return ("informational", 15, "Mensaje enviado sin un caso abierto previo.", False)

    # H4 (issue #195): un mensaje de otra dirección propia confirmada (otro
    # buzón conectado del mismo usuario) no es de un tercero externo.
    own = own_address_set(own_addresses)
    if own and normalize_address(sender) in own:
        return (
            "review",
            30,
            "Mensaje de una dirección propia del usuario (otro buzón conectado); no se trata como externo ni crea caso automáticamente.",
            False,
        )

    # P0.1: una alerta que pide confirmar actividad o reporta actividad
    # sospechosa requiere acción; ninguna regla informativa posterior la anula.
    if requires_security_action(short_text):
        return (
            "action_required",
            90,
            "Alerta de seguridad que pide confirmar una actividad o reporta actividad sospechosa. Verifica desde el sitio oficial, no desde enlaces del correo.",
            True,
        )

    # P0.2: un caso abierto relacionado no convierte un recibo pagado o una
    # cancelación en acción pendiente. Se vincula como evidencia informativa.
    if existing_case is not None and _text_has_any(short_text, INFORMATIONAL_UPDATE_TERMS):
        return (
            "informational",
            40,
            "Recibo o cancelación relacionado con un caso abierto; se agrega como evidencia sin crear acción pendiente ni cerrar el caso.",
            True,
        )

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
        # P0.2: el mensaje sigue la clasificación por su propio contenido; el
        # caso abierto solo determina la vinculación (existing_case viene de
        # hilo, In-Reply-To/References o evidencia corroborada, nunca del
        # asunto solo).
        linked = _classify_by_content(message, subject, short_text, labels, self_delivered)
        if linked[0] == "action_required":
            return linked
        return (linked[0], linked[1], "Continuación de un caso abierto: " + linked[2], True)
    return _classify_by_content(message, subject, short_text, labels, self_delivered)


def _classify_by_content(
    message: dict[str, Any],
    subject: str,
    short_text: str,
    labels: set[str],
    self_delivered: bool,
) -> tuple[str, int, str, bool]:
    sender = str(message.get("sender") or "")

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


# CONC-01: reclamación atómica por mensaje. Un UPDATE condicionado (una sola
# sentencia en Postgres, atómica a nivel fila) marca el mensaje como
# "classifying"; solo el trabajador que recibe la fila de vuelta lo procesa.
# La reclamación caduca para que un proceso muerto no deje mensajes atascados.
CLAIM_CATEGORY = "classifying"
RETRY_CATEGORY = "retry_pending"
CLAIM_LEASE = timedelta(minutes=10)


def _iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _claim_message(client: Any, message_id: str) -> bool:
    now = datetime.now(timezone.utc)
    stale = '"' + _iso_z(now - CLAIM_LEASE) + '"' 
    response = (
        client.table("communication_messages")
        .update({"triage_category": CLAIM_CATEGORY, "triaged_at": _iso_z(now)})
        .eq("id", message_id)
        .eq("case_processed", False)
        .or_(
            "triage_category.is.null,"
            f"triage_category.neq.{CLAIM_CATEGORY},"
            f"triaged_at.lt.{stale}"
        )
        .execute()
    )
    data = getattr(response, "data", None)
    return bool(data)


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
        _sender_parts,
        message_reply_ids,
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

    # H4 (issue #195): identidad propia a nivel usuario = correos de todos los
    # buzones conectados del workspace. Sin esquema nuevo; si la consulta
    # falla se usa solo el correo del buzón actual.
    own_addresses = own_address_set([account.get("email")])
    try:
        own_addresses |= own_address_set(
            row.get("email")
            for row in _rows(
                client.table("communication_accounts")
                .select("email")
                .eq("workspace_id", workspace_id)
                .execute()
            )
        )
    except Exception:
        pass

    if message_ids is not None and not message_ids:
        messages: list[dict[str, Any]] = []
    else:
        query = (
            client.table("communication_messages")
            .select(
                "id,thread_id,account_id,external_message_id,sender,"
                "recipients,cc,bcc,subject,body_text,snippet,"
                "received_at,labels,is_unread,direction,case_processed,"
                "in_reply_to,references_header,triage_category"
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

    from app.services.brain_v1 import brain_v1_enabled

    if brain_v1_enabled():
        from app.services.brain_v1.engine import classify_pending_messages_v1

        return classify_pending_messages_v1(
            client=client,
            account_id=account_id,
            workspace_id=workspace_id,
            messages=messages,
        )
    processed = 0
    created_cases = 0
    linked_cases = 0
    without_case = 0
    errors = 0
    categories: Counter[str] = Counter()
    error_details: list[dict[str, str]] = []

    skipped_claimed = 0
    for message in messages:
        if not _claim_message(client, str(message["id"])):
            # Otro trabajador lo tiene (o ya quedó procesado): no se cuenta dos veces.
            skipped_claimed += 1
            continue
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
                workspace_id=workspace_id,
                reply_ids=message_reply_ids(message),
                sender_email=_sender_parts(message.get("sender"))[1],
                evidence_text=f"{message.get('subject') or ''}\n{message.get('body_text') or message.get('snippet') or ''}",
            )
            category, score, reason, actionable = classify_message(
                message,
                existing_case=existing_case,
                own_addresses=own_addresses,
            )

            if actionable:
                _, result = process_message(
                    client=client,
                    workspace_id=workspace_id,
                    account_id=account_id,
                    message=message,
                    triage_category=category,
                )
                if result == "rejected":
                    raise RuntimeError("process_message rechazó el mensaje por alcance")
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
                elif result == "already_linked":
                    linked_cases += 1
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

            # Un error aislado no detiene la reclasificación. CONC-01: el primer
            # fallo deja el mensaje pendiente y visible ("retry_pending") para
            # un reintento; el segundo lo cierra en revisión humana. Así nunca
            # se repite infinitamente ni se pierde en silencio.
            final = message.get("triage_category") == RETRY_CATEGORY
            (
                client.table("communication_messages")
                .update(
                    {
                        "case_processed": final,
                        "processed_at": now,
                        "triage_category": "review" if final else RETRY_CATEGORY,
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
            categories["review" if final else RETRY_CATEGORY] += 1
            if final:
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
        "skipped_claimed": skipped_claimed,
        "categories": dict(categories),
        "error_details": error_details,
    }
