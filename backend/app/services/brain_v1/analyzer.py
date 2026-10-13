"""Triage del cerebro v1 (reglas, sin IA).

Confianza por mensaje (C8), documentada:
  base por regla (tabla RULE_CONFIDENCE) + 0.05 si hay clave de documento
  + 0.05 si la fecha tiene evidencia − 0.15 si la fecha es ambigua; tope 0.95.
  Ambiguo (< 0.5) → triage 'review' / estado 'requiere revisión'.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.services.brain_v1.dates import DateResult, extract_dates
from app.services.brain_v1.documents import doc_key, extract_amount, period_key
from app.services.brain_v1.protected import SECURITY_ACTION_RE, fold, is_security_or_code, phishing_suspect, protected_type

BRAIN_VERSION = "brain-v1-etapa1-2"

RULE_CONFIDENCE = {
    "security": 0.9, "verification": 0.9, "payment_confirmation": 0.85, "partial_payment": 0.6,
    "appointment": 0.85, "appointment_cancel": 0.85, "invoice_due": 0.85, "charge_due": 0.75,
    "request": 0.7, "social": 0.9, "promotional": 0.85, "invoice_info": 0.7, "legacy_action": 0.6,
    "legacy_notice": 0.7, "legacy_info": 0.75, "ambiguous": 0.35, "excluded": 0.95, "outbound": 0.7,
    "security_action": 0.9, "phishing_suspect": 0.3, "outbound_wait": 0.8, "bulk": 0.8,
}

VERIFY_RE = re.compile(
    r"(verifica(r)? tu (cuenta|correo|email|direccion)|confirma(r)? tu (correo|email|cuenta|direccion)|"
    r"verify your (email|account|address)|confirm your (email|account|address)|activa tu cuenta|activate your account)"
)
PAYMENT_CONFIRM_RE = re.compile(
    r"(recibimos (tu|su) (pago|abono)|pago (recibido|aplicado|exitoso|confirmado|registrado|acreditado)|confirmacion de pago|"
    r"gracias por (tu|su) pago|payment (received|confirmed|successful|processed)|we received your payment|"
    r"thank you for your payment|abono (aplicado|recibido)|comprobante de pago|"
    # A5 (Etapa 1.2): "Pago de servicio aplicado", "Se realizó el pago", "tu pago fue procesado".
    r"pago\b[^.\n]{0,30}\b(aplicad|realizad|procesad|exitos|acreditad|efectuad|completad)|"
    r"se (realizo|aplico|proceso|acredito|efectuo|registro) (el|tu|su|un) (pago|abono)|"
    r"recibimos un abono|payment[^.\n]{0,20}(was |has been )?(processed|applied|completed|successful))"
)
NEGATED_PAYMENT_RE = re.compile(
    r"(\bno (hemos )?(recibido|registrado)|\bnot (yet )?received|have not received|\baun no|sin recibir|"
    r"rechazad|declinad|declined|failed|no (se )?(pudo|pudimos) (procesar|realizar|aplicar)|could not be processed|fallido)"
)
PARTIAL_RE = re.compile(r"(pago parcial|abono parcial|partial payment|saldo restante|remaining balance|resta(nte)? por pagar|"
                        r"saldo pendiente|\babono\b|remaining)")
APPT_CANCEL_RE = re.compile(
    r"((cita|appointment|consulta|reunion|meeting).{0,60}(cancelad|cancelled|canceled)|"
    r"(cancelamos|cancelacion de|hemos cancelado|has been cancel+ed).{0,30}(cita|appointment|consulta)?)"
)
APPT_RE = re.compile(
    r"((cita|appointment|consulta).{0,60}(confirmad|agendad|programad|confirmed|scheduled|booked|reservad)|"
    r"(confirmamos|confirmed|recordatorio de) (tu |su |your )?(cita|appointment|consulta)|appointment reminder)"
)
# A9 (Etapa 1.2): cita reprogramada → actualiza la cita existente con la nueva fecha explícita.
APPT_RESCHEDULE_RE = re.compile(
    r"((cita|appointment|consulta).{0,60}(reprogramad|rescheduled|reagendad|cambiada (al|para))|"
    r"(reprogramamos|reagendamos|rescheduled) (tu |su |your )?(cita|appointment|consulta))"
)
# A8 (Etapa 1.2): correo saliente que deja al usuario esperando algo con fecha.
WAIT_RE = re.compile(
    r"(quedo (en espera|atento|pendiente) de|quedamos (en espera|atentos|pendientes) de|en espera de (su|tu)|"
    r"espero (su|tu) (respuesta|cotizacion|confirmacion|envio|propuesta)|"
    r"(awaiting|look forward to|waiting for) (your|the) (reply|response|quote|quotation|confirmation|proposal))"
)

PAY_DEMAND_RE = re.compile(
    r"(favor de (realizar (el|su) )?pag|realic?e (el|su) pago|realiza tu pago|\bpaga\b|\bpague\b|\bpagar\b|liquida|liquide|"
    r"pago pendiente|pendiente de pago|saldo pendiente|adeudo|payment due|amount due|please pay|pay (now|by|before)|"
    r"\bdue (on|by|date)\b|is due|evitar (la )?suspension|cuanto antes|fecha limite de pago|vence|vencimiento)"
)
PROMO_RE = re.compile(
    r"(descuento|% off|\boferta|promo|cupon|coupon|\bsale\b|newsletter|boletin|no te pierdas|ultimas horas|solo hoy|"
    r"black friday|buen fin|hot sale|envio gratis|free shipping|nuevos productos|novedades|webinar gratuito|"
    r"cancelar suscripcion|darte de baja|unsubscribe|meses sin intereses|aprovecha|exclusiv)"
)
REQUEST_RE = re.compile(
    r"(favor de (enviar|confirmar|revisar|mandar|firmar)|por favor (envia|envie|confirma|confirme|revisa|revise|manda|firma)|"
    r"please (send|confirm|review|sign|submit)|se solicita|solicito que|necesitamos que|requerimos que|"
    r"(puedes|podrias) (enviar|confirmar|mandar)|can you (send|confirm)|could you (send|confirm)|"
    r"te pido|le pido|nos (puedes|podrias)|enviame|envianos|mandame)"
)
INVOICE_TERM_RE = re.compile(
    r"(factura|cfdi|recibo|invoice|\bbill\b|estado de cuenta|statement|\bcargo\b|cobro|cobranza|adeudo|saldo|"
    r"aviso de pago|mensualidad|colegiatura|predial|pedido|order|orden)"
)
SOCIAL_LABEL = "CATEGORY_SOCIAL"
PROMO_LABEL = "CATEGORY_PROMOTIONS"


@dataclass
class Analysis:
    rule: str
    triage: str
    actionable: bool
    confidence: float
    reason: str
    protected: str | None = None
    doc_key: str | None = None
    amount: float | None = None
    dates: DateResult = field(default_factory=DateResult)
    brand: str = ""
    sender_domain: str = ""
    suppressed: bool = False
    key_source: str = "folio"
    bulk: bool = False
    reschedule: bool = False
    phishing_brand: str | None = None

    def signals(self) -> dict[str, Any]:
        return {
            "brain_version": BRAIN_VERSION, "rule": self.rule, "protected": self.protected,
            "doc_key": self.doc_key, "key_source": self.key_source if self.doc_key else None, "amount": self.amount, "confidence": self.confidence,
            "suppressed": self.suppressed, "bulk": self.bulk, "reschedule": self.reschedule,
            "phishing_brand": self.phishing_brand, **self.dates.as_metadata(),
        }


def _confidence(rule: str, *, doc: bool, dates: DateResult) -> float:
    value = RULE_CONFIDENCE.get(rule, 0.5)
    if doc:
        value += 0.05
    if dates.due_evidence or dates.event_evidence:
        value += 0.05
    if dates.date_ambiguous:
        value -= 0.15
    return round(max(0.05, min(value, 0.95)), 2)


def _with_period(analysis: Analysis, subject: str, body: str, received: Any) -> Analysis:
    """C4b: factura o cobro sin folio → clave marca + periodo (mes de facturación o de recepción)."""
    if not analysis.doc_key:
        analysis.doc_key = period_key(analysis.brand, subject, body, received)
        analysis.key_source = "periodo"
    return analysis


def _headers(message: dict[str, Any]) -> dict[str, str]:
    """A10: cabeceras del mensaje (columna headers o metadata.headers), con nombres en minúsculas."""
    raw = message.get("headers")
    if not isinstance(raw, dict):
        meta = message.get("metadata") if isinstance(message.get("metadata"), dict) else {}
        raw = meta.get("headers") if isinstance(meta.get("headers"), dict) else {}
    return {str(k).lower(): str(v or "") for k, v in raw.items()}


def is_bulk(headers: dict[str, str]) -> bool:
    """A10: List-Unsubscribe o List-Id = correo masivo (boletín, lista, campaña)."""
    return bool(headers.get("list-unsubscribe", "").strip() or headers.get("list-id", "").strip())


def analyze(message: dict[str, Any], *, user_verified: bool | None = None) -> Analysis:
    from app.services.case_engine import _sender_parts, brand_of_email
    from app.services.classification_catalog import identify_sender, is_marketing_local_part
    from app.services.import_categories import sender_domain as _domain, social_platform
    from app.services.mail_direction import direction_from_labels, is_self_delivered
    from app.services.safe_case_classifier import _sender_is_automated, _sender_is_promotional

    labels = {str(item).upper() for item in (message.get("labels") or [])}
    sender = str(message.get("sender") or "")
    subject = str(message.get("subject") or "")
    body = str(message.get("body_text") or message.get("snippet") or "")
    text = fold(f"{subject}\n{body[:3000]}")
    _, sender_email = _sender_parts(sender)
    brand = brand_of_email(sender_email)
    domain = _domain(sender)
    received = message.get("received_at")
    headers = _headers(message)
    bulk = is_bulk(headers)

    def build(rule: str, triage: str, actionable: bool, reason: str, *, kind: str | None = None,
              with_doc: bool = False, protected: str | None = None, suppressed: bool = False) -> Analysis:
        dates = extract_dates(subject, body, received, kind=kind) if actionable or kind else DateResult()
        key = doc_key(brand, subject, body) if with_doc else None
        conf = _confidence(rule, doc=bool(key), dates=dates)
        return Analysis(rule, triage, actionable, conf, reason, protected=protected, doc_key=key,
                        amount=extract_amount(subject, body) if with_doc else None, dates=dates,
                        brand=brand, sender_domain=domain, suppressed=suppressed, bulk=bulk)

    if "DRAFT" in labels or "SPAM" in labels or "TRASH" in labels:
        return build("excluded", "informational", False, "Borrador, spam o papelera: fuera del flujo.")
    direction = direction_from_labels(message.get("labels"), message.get("direction"))
    if direction == "outbound" and not is_self_delivered(labels):
        if WAIT_RE.search(text):
            waiting = build("outbound_wait", "waiting_external", True,
                            "Enviaste un correo y quedaste en espera de una respuesta con fecha.", kind="waiting")
            if waiting.dates.due_at:
                return waiting
        return build("outbound", "informational", False, "Mensaje enviado; solo se une a un caso existente del hilo.")

    # A3: marca suplantada + petición de pago/datos + clic o urgencia → revisión, nunca alerta legítima ni cobro.
    phish = phishing_suspect(sender, subject, body)
    if phish:
        result = build("phishing_suspect", "review", False,
                       f"Posible suplantación: menciona {phish} pero el remitente es {domain or 'otro dominio'}, y pide pago o datos.")
        result.phishing_brand = phish
        return result

    prot = protected_type(sender, subject, body, headers=headers)

    # C1: seguridad y códigos primero, aunque el remitente sea una red social.
    # A7: un código nunca abre caso, aunque diga "confirma tu cuenta".
    sec = is_security_or_code(sender, subject, body)
    if sec == "code" or (sec and not VERIFY_RE.search(text)):
        if sec == "security" and SECURITY_ACTION_RE.search(text):
            # A2: alerta que pide actuar (contraseña conocida, acceso bloqueado) → caso N1.
            return build("security_action", "action_required", True,
                         "Alerta de seguridad que pide actuar: cambia tu contraseña o revisa el acceso.", protected=sec)
        return build("security", "notice", False,
                     "Alerta de seguridad o código de acceso: protegido, nunca se descarta como ruido.", protected=sec)

    # C7: verificaciones repetidas → un solo elemento agrupado; suprimido si ya está verificado.
    if VERIFY_RE.search(text):
        donexto = brand == "donexto"
        if donexto and user_verified:
            return build("verification", "informational", False,
                         "Verificación de Donexto repetida; tu cuenta ya está verificada (app_metadata.donexto_verified).",
                         suppressed=True)
        return build("verification", "notice", True,
                     "Solicitud de verificación de cuenta; se agrupa en un solo elemento.")

    if PAYMENT_CONFIRM_RE.search(text) and not NEGATED_PAYMENT_RE.search(text):
        rule = "partial_payment" if PARTIAL_RE.search(text) else "payment_confirmation"
        return build(rule, "notice", True, "Confirmación de pago; se busca el caso con el mismo folio.",
                     with_doc=True, protected="invoice")

    if APPT_CANCEL_RE.search(text):
        return build("appointment_cancel", "notice", True, "Cancelación de cita; actualiza la cita existente.",
                     kind="appointment_cancel", protected=prot)
    if APPT_RESCHEDULE_RE.search(text):
        analysis = build("appointment", "notice", True, "Cita reprogramada: se actualiza la fecha de la cita.",
                         kind="appointment", protected=prot or "health")
        analysis.reschedule = True
        if analysis.dates.event_at:
            return analysis
    if APPT_RE.search(text):
        analysis = build("appointment", "action_required", True, "Cita confirmada: compromiso con fecha.",
                         kind="appointment", protected=prot or "health")
        if not analysis.dates.event_at:
            analysis.rule, analysis.triage, analysis.actionable = "ambiguous", "review", False
            analysis.confidence = 0.4
            analysis.reason = "Cita sin fecha clara; requiere revisión."
        return analysis

    identity = identify_sender(sender) or {}
    vertical = str(identity.get("vertical") or "")
    is_social = bool(social_platform(sender)) or vertical == "social" or SOCIAL_LABEL in labels
    if is_social:
        return build("social", "social", False, "Notificación de red social sin acción.")

    marketing = (
        PROMO_LABEL in labels or _sender_is_promotional(sender) or is_marketing_local_part(sender)
        or bool(PROMO_RE.search(text))
    )
    demand = bool(PAY_DEMAND_RE.search(text))
    invoice_term = bool(INVOICE_TERM_RE.search(text))
    promo_terms = bool(PROMO_RE.search(text))

    # C3: factura o cobro que pide pago → accionable aunque el remitente sea desconocido.
    if demand and invoice_term and not promo_terms:
        rule = "invoice_due" if re.search(r"(factura|cfdi|recibo|invoice|\bbill\b|estado de cuenta|statement)", text) else "charge_due"
        return _with_period(build(rule, "action_required", True, "Factura o cobro que pide un pago.",
                                  with_doc=True, protected="invoice"), subject, body, received)
    if bulk and not marketing:
        # A10: correo masivo (lista, aviso automático) → informativo; nunca petición ni pendiente.
        # Si además es publicidad o boletín, cae abajo en "promotional" (convención del corpus).
        return build("bulk", "informational", False,
                     "Correo masivo (List-Unsubscribe/List-Id) sin cobro: informativo, no crea pendiente.", protected=prot)
    if marketing:
        return build("promotional", "promotional", False,
                     "Publicidad o boletín; las palabras 'urgente' o 'último aviso' no crean pendiente.")
    if demand and re.search(r"(saldo|adeudo|cuanto antes|pago pendiente|pendiente de pago|suspension)", text):
        return _with_period(build("charge_due", "action_required", True, "Cobro pendiente sin factura adjunta.",
                                  with_doc=True, protected="invoice"), subject, body, received)
    if REQUEST_RE.search(text) and not _sender_is_automated(sender):
        return build("request", "action_required", True, "Solicitud directa de una persona.", with_doc=True,
                     protected=prot)

    if invoice_term and re.search(r"(factura|cfdi|recibo|invoice|estado de cuenta|statement)", text):
        return build("invoice_info", "notice", False, "Comprobante o estado de cuenta informativo, sin cobro pendiente.",
                     protected=prot)

    # Resto: el clasificador vigente decide; aquí solo se le pone confianza real.
    from app.services.safe_case_classifier import classify_message

    category, score, reason, actionable = classify_message(message, existing_case=None)
    if category == "action_required":
        return build("legacy_action", category, True, reason, with_doc=True, protected=prot)
    if category == "review":
        result = build("ambiguous", "review", False, reason, protected=prot)
        return result
    if category in {"notice"}:
        return build("legacy_notice", category, False, reason, protected=prot)
    return build("legacy_info", category, False, reason, protected=prot)
