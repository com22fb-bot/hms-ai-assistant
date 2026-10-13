"""Motor de casos del cerebro v1 (C2–C9). Solo se usa con BRAIN_V1_ENABLED.

Estados (C9) → columna intelligent_cases.status:
  pendiente=new · en seguimiento=in_progress · programado=scheduled ·
  esperando a otro=waiting_external · resuelto=resolved · sin acción=no_action ·
  requiere revisión=needs_review   (scheduled/no_action/needs_review: migración 20261012_005)
Confianza del caso = máx(confianza de sus mensajes); < 0.5 → needs_review.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from app.services.brain_v1.analyzer import BRAIN_VERSION, Analysis, analyze
from app.services.brain_v1.documents import amounts_compatible, brand_mentioned, extract_doc_token

STATUS_LABELS = {
    "new": "pendiente", "in_progress": "en seguimiento", "scheduled": "programado",
    "waiting_external": "esperando a otro", "resolved": "resuelto", "no_action": "sin acción",
    "needs_review": "requiere revisión",
}
OPEN_V1 = ["new", "analyzing", "in_progress", "delegated", "waiting_internal", "waiting_external", "scheduled", "needs_review"]
GROUP_WINDOW_DAYS = 30
CLOSED_V1 = {"resolved", "closed", "archived", "no_action"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


PRIORITY_RANK = {"low": 0, "normal": 1, "high": 2, "critical": 3}


def _max_priority(*values: Any) -> str:
    known = [str(v) for v in values if str(v) in PRIORITY_RANK]
    return max(known, key=PRIORITY_RANK.__getitem__) if known else "normal"


def _no_null_dates(updates: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    """A6 (Etapa 1.2): una actualización nunca pone due_at/event_at en null si el caso ya tenía valor."""
    for column in ("due_at", "event_at"):
        if column in updates and updates[column] is None and case.get(column):
            updates.pop(column)
    meta = updates.get("metadata")
    if isinstance(meta, dict) and meta.get("event_at") is None and _meta(case).get("event_at"):
        meta["event_at"] = _meta(case)["event_at"]
    return updates


def _open_cases(client: Any, workspace_id: str, *, statuses: list[str] | None = None,
                **filters: str) -> list[dict[str, Any]]:
    from app.services.case_engine import _rows

    query = client.table("intelligent_cases").select("*").eq("workspace_id", workspace_id)
    for column, value in filters.items():
        query = query.eq(column.replace("__", "->>"), value)
    rows = _rows(query.in_("status", statuses or OPEN_V1).order("last_activity_at", desc=True).limit(50).execute())
    rows.sort(key=lambda r: str(r.get("last_activity_at") or ""), reverse=True)
    return rows


def _meta(case: dict[str, Any]) -> dict[str, Any]:
    value = case.get("metadata")
    return value if isinstance(value, dict) else {}


def find_case_v1(client: Any, *, workspace_id: str, account_id: str, message: dict[str, Any],
                 analysis: Analysis, normalized_subject: str) -> dict[str, Any] | None:
    key = analysis.doc_key
    if key:
        rows = _open_cases(client, workspace_id, metadata__doc_key=key)
        if rows:
            return rows[0]
        if analysis.key_source == "folio" and analysis.rule in {"invoice_due", "charge_due"}:
            # f) (cierre v1): copia del mismo folio en otro buzón después de pagado → se une al caso resuelto,
            # sin reabrirlo ni duplicarlo.
            rows = _open_cases(client, workspace_id, statuses=["resolved", "closed"], metadata__doc_key=key)
            if rows:
                return rows[0]
    if analysis.rule == "verification":
        # A7: el grupo de verificaciones de terceros vive en no_action; los repetidos se le suman.
        rows = _open_cases(client, workspace_id, statuses=OPEN_V1 + ["no_action"],
                           metadata__group_key=f"{analysis.brand}:account_verification")
        return rows[0] if rows else None
    if analysis.rule in {"appointment", "appointment_cancel", "booking"}:
        rows = _open_cases(client, workspace_id, metadata__appt_key=analysis.sender_domain)
        if analysis.rule == "appointment_cancel":
            when = (analysis.dates.event_at or "")[:10]
            same_day = [r for r in rows if when and str(_meta(r).get("event_at") or "")[:10] == when]
            return (same_day or rows or [None])[0]
        if analysis.reschedule:
            return rows[0] if rows else None  # A9: la reprogramación mueve la cita abierta del mismo remitente
        when = (analysis.dates.event_at or "")[:10]
        same_day = [r for r in rows if when and str(_meta(r).get("event_at") or "")[:10] == when]
        return same_day[0] if same_day else None  # una cita nueva en otra fecha es otro compromiso
    thread_id = message.get("thread_id")
    if thread_id:
        from app.services.case_engine import _rows

        rows = _rows(
            client.table("intelligent_cases").select("*").eq("account_id", account_id)
            .eq("primary_thread_id", str(thread_id)).in_("status", OPEN_V1).limit(5).execute()
        )
        for row in rows:
            if _meta(row).get("doc_key") in (None, key):
                return row
    if normalized_subject and not key and analysis.rule not in {"payment_confirmation", "partial_payment"}:
        for row in _open_cases(client, workspace_id, normalized_subject=normalized_subject):
            if not _meta(row).get("doc_key"):
                return row
    return None


def _cross_sender_payment_case(client: Any, workspace_id: str, analysis: Analysis, text: str) -> dict[str, Any] | None:
    """C5b: pago confirmado por otro remitente (p. ej. un banco) o sin folio.

    Coincide si un caso abierto de factura/cobro es de la misma marca (o el texto la menciona) y el importe
    es compatible, o si el folio del pago aparece en el caso. Nunca cierra: queda "posible pago, confirmar".
    """
    token = extract_doc_token(text, "")
    for row in _open_cases(client, workspace_id):
        meta = _meta(row)
        if meta.get("rule") not in {"invoice_due", "charge_due"}:
            continue
        if token and str(meta.get("doc_key") or "").endswith(":" + token):
            return row
        if token and (meta.get("key_source") or "folio") == "folio":
            continue  # C4: folios distintos nunca se unen
        same_brand = meta.get("brand") == analysis.brand or brand_mentioned(meta.get("brand"), text)
        if same_brand and amounts_compatible(meta.get("amount"), analysis.amount):
            return row
    return None


def _priority(analysis: Analysis, text: str, received_at: str) -> tuple[str, int]:
    from app.services.case_engine import _risk_and_priority

    risk, priority, level = _risk_and_priority(text=text, is_unread=False, reminder_count=0)
    if analysis.rule == "verification":
        return "low", 1
    if analysis.rule == "security_action":
        # Política única de seguridad: crítica solo con urgencia explícita + riesgo significativo; si no, N2.
        return ("critical", 3) if analysis.severity == "critical" else ("normal", 2)
    if analysis.rule == "security_unverified":
        return "normal", 2  # remitente no confiable: revisión, nunca crítica automática
    if analysis.rule == "bill_followup":
        return "normal", 1  # sin vencimiento: seguimiento, nunca urgencia inventada
    if analysis.rule == "outbound_wait":
        return "normal", 1  # A8: la espera es del otro; el plazo no es un riesgo del usuario
    if analysis.rule in {"appointment", "booking"}:
        return _scheduled_priority(analysis.dates.event_at, received_at), 1  # A14
    if analysis.rule in {"invoice_due", "charge_due", "request", "appointment"}:
        priority = "normal" if priority == "low" else priority
        due = analysis.dates.due_at or analysis.dates.event_at
        if due:
            try:
                days = (datetime.fromisoformat(due) - datetime.fromisoformat(received_at.replace("Z", "+00:00"))).days
                if days <= 3:
                    priority = "high" if priority != "critical" else priority
            except ValueError:
                pass
    return priority, level


PRIORITY_LEVEL = {"critical": "N1", "high": "N1", "normal": "N2", "low": "N3"}


def _scheduled_priority(event_at: str | None, received_at: str | None) -> str:
    """A14 (Etapa 1.3): lo programado es N3; N2 si el evento es dentro de 3 días o menos. Nunca N1 por ser cita."""
    if not event_at or not received_at:
        return "low"
    try:
        start = datetime.fromisoformat(str(event_at).replace("Z", "+00:00"))
        got = datetime.fromisoformat(str(received_at).replace("Z", "+00:00"))
    except ValueError:
        return "low"
    return "normal" if (start - got).total_seconds() <= 3 * 86400 else "low"


def process_message_v1(*, client: Any, workspace_id: str, account_id: str, message: dict[str, Any],
                       analysis: Analysis) -> tuple[str | None, str]:
    """Devuelve (case_id, resultado): created | linked | resolved | possible_payment | no_case."""
    from app.services.case_engine import (
        _classify_case_type, _message_direction, _recipient_emails, _requested_action, _sender_parts,
        _to_iso, _update_learning, _upsert_participant, _first_row, normalize_subject,
    )
    from app.services.event_engine import create_case_event
    from app.utils.html_text import strip_css_noise

    message_id = str(message["id"])
    # Control 7.2 (idempotencia): un mensaje ya ligado a un caso nunca vuelve a crear, unir ni cerrar nada.
    from app.services.case_engine import _rows as _rows_q

    already = _rows_q(client.table("case_messages").select("case_id").eq("message_id", message_id).limit(1).execute())
    if already:
        return str(already[0]["case_id"]), "already_linked"
    received_at = _to_iso(message.get("received_at"))
    subject = strip_css_noise(str(message.get("subject") or "")) or "(Sin asunto)"
    body = str(message.get("body_text") or message.get("snippet") or "")
    text = f"{subject}\n{body}"
    normalized = normalize_subject(subject)
    direction = _message_direction(message)
    sender_name, sender_email = _sender_parts(message.get("sender"))
    snippet = body.strip()[:240]
    case = find_case_v1(client, workspace_id=workspace_id, account_id=account_id, message=message,
                        analysis=analysis, normalized_subject=normalized)
    result = "linked"

    cross_sender = False
    if analysis.rule in {"payment_confirmation", "partial_payment"} and not case:
        case = _cross_sender_payment_case(client, workspace_id, analysis, text)
        cross_sender = case is not None
    if analysis.rule in {"payment_confirmation", "partial_payment"}:
        if not case:
            return None, "no_case"
        meta = _meta(case)
        strong = (
            not cross_sender
            and (meta.get("key_source") or "folio") == "folio"
            and analysis.rule == "payment_confirmation" and analysis.doc_key
            and meta.get("doc_key") == analysis.doc_key
            and amounts_compatible(meta.get("amount"), analysis.amount)
        )
        evidence = {"message_id": message_id, "snippet": snippet, "amount": analysis.amount, "doc_key": analysis.doc_key,
                    "payment_source": "otro_remitente" if cross_sender else "mismo_remitente"}
        if strong:
            # A11: un caso resuelto baja a N3; la prioridad más alta que tuvo queda en metadata.
            peak = _max_priority(case.get("priority"), meta.get("priority_max"))
            client.table("intelligent_cases").update({
                "status": "resolved", "resolved_at": received_at, "last_activity_at": received_at,
                "source_count": int(case.get("source_count") or 0) + 1, "waiting_on": "none", "priority": "low",
                "metadata": {**meta, "payment_status": "confirmed", "payment_evidence": evidence,
                             "priority_max": peak, "priority_max_level": PRIORITY_LEVEL[peak]},
            }).eq("id", case["id"]).execute()
            create_case_event(client=client, workspace_id=workspace_id, case_id=str(case["id"]), message_id=message_id,
                              event_type="payment_confirmed", level=2, title="Pago confirmado",
                              description=f"Mismo folio e importe compatible. Evidencia: {snippet[:160]}",
                              dedupe_key=f"payment_confirmed:{message_id}", metadata=evidence)
            result = "resolved"
        else:
            client.table("intelligent_cases").update({
                "last_activity_at": received_at, "source_count": int(case.get("source_count") or 0) + 1,
                "metadata": {**meta, "payment_status": "possible", "payment_hint": "posible pago, confirmar",
                             "payment_evidence": evidence},
            }).eq("id", case["id"]).execute()
            create_case_event(client=client, workspace_id=workspace_id, case_id=str(case["id"]), message_id=message_id,
                              event_type="possible_payment", level=2, title="Posible pago, confirmar",
                              description="Coincidencia parcial (folio o importe); el caso sigue abierto.",
                              dedupe_key=f"possible_payment:{message_id}", metadata=evidence)
            result = "possible_payment"
    elif analysis.rule == "appointment_cancel":
        if not case:
            return None, "no_case"
        client.table("intelligent_cases").update({
            "status": "no_action", "closed_at": received_at, "last_activity_at": received_at,
            "source_count": int(case.get("source_count") or 0) + 1,
            "metadata": {**_meta(case), "cancelled": True, "cancel_evidence": {"message_id": message_id, "snippet": snippet}},
        }).eq("id", case["id"]).execute()
        create_case_event(client=client, workspace_id=workspace_id, case_id=str(case["id"]), message_id=message_id,
                          event_type="appointment_cancelled", level=2, title="Cita cancelada",
                          description=snippet[:200], dedupe_key=f"appointment_cancelled:{message_id}")
        result = "linked"
    elif case is None:
        priority, level = _priority(analysis, text, received_at)
        if analysis.rule in {"appointment", "booking"}:
            status = "scheduled"
        elif analysis.rule == "verification" and analysis.brand != "donexto":
            status = "no_action"  # A7: verificación de terceros: un elemento agrupado, nunca pendiente
        elif analysis.rule == "outbound_wait":
            status = "waiting_external"  # A8
        elif analysis.confidence < 0.5:
            status = "needs_review"
        else:
            status = "new"
        dates = analysis.dates
        metadata = {
            "created_by": BRAIN_VERSION, "rule": analysis.rule, "initial_message_direction": direction,
            "doc_key": analysis.doc_key, "key_source": analysis.key_source if analysis.doc_key else None,
            "brand": analysis.brand, "amount": analysis.amount, "protected": analysis.protected,
            "message_confidences": {message_id: analysis.confidence},
            "evidence": [{"message_id": message_id, "snippet": snippet}],
            "event_at": dates.event_at, "event_evidence": dates.event_evidence,
            "due_evidence": dates.due_evidence, "date_ambiguous": dates.date_ambiguous,
            "ambiguous_evidence": dates.ambiguous_evidence, "priority_level": PRIORITY_LEVEL[priority],
            "priority_max": priority, "priority_max_level": PRIORITY_LEVEL[priority],
        }
        if analysis.rule == "verification":
            metadata["group_key"] = f"{analysis.brand}:account_verification"
        if analysis.rule in {"appointment", "booking"}:
            metadata["appt_key"] = analysis.sender_domain
        response = client.table("intelligent_cases").insert({
            "workspace_id": workspace_id, "account_id": account_id, "primary_thread_id": message.get("thread_id"),
            "title": subject, "normalized_subject": normalized,
            "case_type": "meeting" if analysis.rule in {"appointment", "booking"} else _classify_case_type(text),
            "status": status, "priority": priority, "risk_score": 50 if priority in {"high", "critical"} else 30,
            "confidence": analysis.confidence, "summary": snippet or None, "requested_action": _requested_action(text),
            "requester_name": sender_name if direction == "inbound" else None,
            "requester_email": sender_email if direction == "inbound" else None,
            "waiting_on": "external" if status == "waiting_external" else "internal", "opened_at": received_at, "last_activity_at": received_at,
            "due_at": dates.due_at, "event_at": dates.event_at,
            "source_count": 1, "reminder_count": 0, "metadata": metadata,
        }).execute()
        case = _first_row(response)
        if not case:
            raise RuntimeError("Supabase no confirmó la creación del caso.")
        create_case_event(client=client, workspace_id=workspace_id, case_id=str(case["id"]), message_id=message_id,
                          event_type="case_created", level=max(level, 2), title="Nuevo caso detectado",
                          description=subject, dedupe_key=f"case_created:{message_id}",
                          metadata={"rule": analysis.rule, "confidence": analysis.confidence})
        result = "created"
    else:
        meta = _meta(case)
        confidences = {**(meta.get("message_confidences") or {}), message_id: analysis.confidence}
        updates: dict[str, Any] = {
            "last_activity_at": received_at, "source_count": int(case.get("source_count") or 0) + 1,
            "confidence": max(confidences.values()),
            "metadata": {**meta, "message_confidences": confidences,
                         "evidence": (meta.get("evidence") or [])[-9:] + [{"message_id": message_id, "snippet": snippet}]},
        }
        reminder = (analysis.rule in {"invoice_due", "charge_due", "request", "legacy_action", "verification"}
                    and case.get("status") not in CLOSED_V1)
        if reminder:
            updates["reminder_count"] = int(case.get("reminder_count") or 0) + 1
        # C2: un recordatorio puede completar la fecha, nunca sobrescribir una con evidencia.
        if analysis.dates.due_at and not case.get("due_at"):
            updates["due_at"] = analysis.dates.due_at
            updates["metadata"]["due_evidence"] = analysis.dates.due_evidence
        if reminder:
            # A11: se registra la prioridad máxima vista (la prioridad del caso no cambia aquí).
            new_priority, _ = _priority(analysis, text, received_at)
            current = str(case.get("priority") or "normal")
            peak = _max_priority(current, new_priority, meta.get("priority_max"))
            updates["metadata"]["priority_max"] = peak
            updates["metadata"]["priority_max_level"] = PRIORITY_LEVEL[peak]
        if analysis.reschedule and analysis.dates.event_at:
            # A9 + A6: solo otra fecha explícita con evidencia cambia event_at.
            updates["event_at"] = analysis.dates.event_at
            updates["metadata"]["event_at"] = analysis.dates.event_at
            updates["metadata"]["event_evidence"] = analysis.dates.event_evidence
            updates["metadata"]["previous_event_at"] = case.get("event_at") or meta.get("event_at")
            if case.get("status") in {"new", "needs_review"}:
                updates["status"] = "scheduled"
            if case.get("status") in {"scheduled", "new", "needs_review"}:
                updates["priority"] = _scheduled_priority(analysis.dates.event_at, received_at)  # A14
        if direction == "outbound":
            updates["status"] = "waiting_external" if case.get("status") in {"new", "in_progress"} else case.get("status")
            updates["waiting_on"] = "external"
        if case.get("status") == "needs_review" and updates["confidence"] >= 0.5:
            updates["status"] = "new"
        _no_null_dates(updates, case)
        client.table("intelligent_cases").update(updates).eq("id", case["id"]).execute()
        create_case_event(client=client, workspace_id=workspace_id, case_id=str(case["id"]), message_id=message_id,
                          event_type="appointment_rescheduled" if analysis.reschedule else
                          "reminder_received" if reminder else "external_reply", level=2,
                          title="Recordatorio recibido" if reminder else "Nueva evidencia recibida",
                          description=snippet[:200], dedupe_key=f"v1_link:{message_id}")

    case_id = str(case["id"])
    client.table("case_messages").insert({
        "case_id": case_id, "message_id": message_id, "relation_type": "evidence",
        "is_primary": result == "created", "linked_at": received_at,
    }).execute()
    if sender_email:
        _upsert_participant(client=client, case_id=case_id, email=sender_email, display_name=sender_name,
                            participant_role="requester" if direction == "inbound" else "sender", seen_at=received_at)
    for recipient in _recipient_emails(message):
        _upsert_participant(client=client, case_id=case_id, email=recipient, display_name=None,
                            participant_role="recipient", seen_at=received_at)
    _update_learning(client=client, workspace_id=workspace_id, case_type=_classify_case_type(text),
                     requester_email=sender_email, recipient_emails=_recipient_emails(message))
    return case_id, result


def workspace_user_verified(client: Any, workspace_id: str) -> bool | None:
    """C7: lee app_metadata.donexto_verified del dueño del workspace (security/donexto_verified.py).

    None si no se puede confirmar → no se suprime nada (se agrupa).
    """
    from app.security.donexto_verified import read_donexto_verified
    from app.services.case_engine import _rows

    try:
        members = _rows(client.table("workspace_members").select("user_id,role").eq("workspace_id", workspace_id).limit(5).execute())
        owner = next((m for m in members if m.get("role") == "owner"), members[0] if members else None)
        if not owner:
            return None
        user = client.auth.admin.get_user_by_id(str(owner["user_id"]))
        user = getattr(user, "user", user)
        app_metadata = getattr(user, "app_metadata", None) or (user.get("app_metadata") if isinstance(user, dict) else None)
        return read_donexto_verified(app_metadata)
    except Exception:
        return None


def classify_pending_messages_v1(*, client: Any, account_id: str, workspace_id: str, messages: list[dict[str, Any]],
                                 user_verified: bool | None = None) -> dict[str, Any]:
    from app.services.case_engine import normalize_subject

    if user_verified is None:
        user_verified = workspace_user_verified(client, workspace_id)
    ordered = sorted(messages, key=lambda m: str(m.get("received_at") or ""))  # cronológico: factura → recordatorio → pago
    counters: Counter[str] = Counter()
    categories: Counter[str] = Counter()
    error_details: list[dict[str, str]] = []
    for message in ordered:
        now = _now()
        try:
            analysis = analyze(message, user_verified=user_verified)
            case_id, outcome = (None, "no_case")
            if analysis.actionable:
                case_id, outcome = process_message_v1(client=client, workspace_id=workspace_id, account_id=account_id,
                                                      message=message, analysis=analysis)
            elif message.get("thread_id") and analysis.rule in {"outbound", "legacy_info", "ambiguous"}:
                # Respuesta dentro de un hilo con caso abierto: se une como evidencia (comportamiento vigente).
                existing = find_case_v1(client, workspace_id=workspace_id, account_id=account_id, message=message,
                                        analysis=analysis, normalized_subject="")
                if existing:
                    case_id, outcome = process_message_v1(client=client, workspace_id=workspace_id,
                                                          account_id=account_id, message=message, analysis=analysis)
            triage = analysis.triage
            if outcome == "no_case" and analysis.rule in {"payment_confirmation", "partial_payment", "appointment_cancel"}:
                triage = "notice"
            client.table("communication_messages").update({
                "normalized_subject": normalize_subject(str(message.get("subject") or "")),
                "case_processed": True, "processed_at": now, "triage_category": triage,
                "actionability_score": int(round(analysis.confidence * 100)),
                "triage_reason": analysis.reason, "triaged_at": now,
                "brain_confidence": analysis.confidence, "brain_signals": analysis.signals(),
            }).eq("id", str(message["id"])).execute()
            counters[outcome] += 1
            categories[triage] += 1
        except Exception as error:  # un error aislado no detiene el lote
            counters["errors"] += 1
            client.table("communication_messages").update({
                "case_processed": True, "processed_at": now, "triage_category": "review", "actionability_score": 0,
                "triage_reason": "Revisión necesaria por incidencia técnica: " + str(error)[:1000], "triaged_at": now,
            }).eq("id", str(message.get("id") or "")).execute()
            categories["review"] += 1
            if len(error_details) < 20:
                error_details.append({"message_id": str(message.get("id") or ""), "error": str(error)[:500]})
    processed = sum(v for k, v in counters.items() if k != "errors") + counters["errors"]
    return {
        "status": "ok" if not counters["errors"] else "partial", "classifier_version": BRAIN_VERSION,
        "found": len(messages), "processed": processed, "created_cases": counters["created"],
        "linked_cases": counters["linked"] + counters["resolved"] + counters["possible_payment"],
        "resolved_cases": counters["resolved"], "possible_payments": counters["possible_payment"],
        "without_case": counters["no_case"] + counters["errors"], "errors": counters["errors"],
        "categories": dict(categories), "error_details": error_details,
    }
