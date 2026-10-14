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

BRAIN_VERSION = "brain-v1-post-lote4"

RULE_CONFIDENCE = {
    "security": 0.9, "verification": 0.9, "payment_confirmation": 0.85, "partial_payment": 0.6,
    "appointment": 0.85, "appointment_cancel": 0.85, "invoice_due": 0.85, "charge_due": 0.75,
    "request": 0.7, "social": 0.9, "promotional": 0.85, "invoice_info": 0.7, "legacy_action": 0.6,
    "legacy_notice": 0.7, "legacy_info": 0.75, "ambiguous": 0.35, "excluded": 0.95, "outbound": 0.7,
    "security_action": 0.9, "security_unverified": 0.4, "bill_followup": 0.45, "phishing_suspect": 0.3, "outbound_wait": 0.8, "bulk": 0.8,
    "booking": 0.85, "auto_notice": 0.8,
    # Post lote 4: reglas específicas que antes caían en "ambiguous".
    "bill_settled": 0.85, "booking_pending": 0.8, "booking_cancel": 0.85, "renewal_upcoming": 0.8,
    "renewal_done": 0.85, "renewal_action": 0.75, "order_notice": 0.8, "stock_alert": 0.75,
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
    r"recibimos un abono|recibimos (un|el) pago|confirmamos (nuevamente |de nuevo )?(el|tu|su|un) (pago|abono)|\bpagaste\b|\byou paid\b|payment[^.\n]{0,20}(was |has been )?(processed|applied|completed|successful))"
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
    r"(confirmamos|confirmed|recordatorio de) (tu |su |your )?(cita|appointment|consulta)|appointment reminder|"
    # A12 (Etapa 1.3): "Confirmación de cita para pasaporte"
    r"confirmacion de (tu |su |la )?(cita|consulta))"
)
# A12 (Etapa 1.3): confirmaciones automáticas de reservación, itinerario o registro (plantillas).
BOOKING_RE = re.compile(
    r"(reservacion confirmada|reserva confirmada|confirmacion de (tu |su )?(reservacion|reserva|registro|boleto|vuelo)|"
    r"(tu|su) (registro|reservacion|reserva) (esta |fue |ha sido )?confirmad|registro confirmado|tu itinerario|itinerario de viaje|"
    r"pase de abordar|boarding pass|booking (is )?confirmed|reservation confirmed|your (itinerary|booking|reservation)|"
    r"registration (is )?confirmed|you'?re registered|e-?ticket|"
    # Política de reservas (post lote 3): vuelos, hospedaje y entradas, solo confirmaciones firmes.
    r"(tu|su|your) (vuelo|flight) (esta |fue |ha sido |is |has been )?(confirmad|confirmed)|vuelo confirmado|flight confirmed|"
    r"confirmacion de (tu |su )?(hospedaje|estancia|alojamiento|hotel|entrada|entradas|boletos)|"
    r"(tus?|sus?) (hospedaje|estancia|alojamiento|entrada|entradas|boleto|boletos) (esta |estan |fue |fueron |ha sido )?confirmad|"
    r"(hotel|stay|lodging) (reservation|booking) (is )?confirmed|your stay is confirmed|"
    r"(your )?tickets? (is |are )?confirmed|your tickets|order of tickets confirmed)"
)
# Nunca es confirmación firme: solicitud, propuesta, cancelación, pendiente o tentativa.
BOOKING_NOT_FIRM_RE = re.compile(
    r"(cancelad|cancelled|canceled|solicitud de (reserva|reservacion)|booking request|reservation request|propuesta|"
    r"proposal|por confirmar|pendiente de confirmacion|pending confirmation|awaiting confirmation|tentativ|on hold|"
    r"\bhold\b|lista de espera|waitlist|cotizacion|quote)"
)
TRANSACTIONAL_LOCALS = re.compile(
    r"^(reservas?|reservaciones|reservations?|booking|bookings|citas|agenda|eventos?|events?|registro|registros|"
    r"itinerarios?|tickets?|boletos|viajes|travel|confirmaciones|confirmations?|avisos|notificaciones|alertas|alerts|"
    r"pedidos|orders?|envios|shipping|devoluciones|returns|resultados|cuentas|accounts|billing|facturacion|"
    r"estados?|estadosdecuenta|facturas|recibos|statements?|invoices?|hospedaje|hotel|hotels|vuelos|flights|itinerary|itineraries|calendar|calendario)$"
)
# A13 (Etapa 1.3): avisos automáticos que no piden nada.
ORDER_NOTICE_RE = re.compile(
    r"(tu pedido (ha sido |fue |esta )?(confirmado|enviado|en camino|entregado)|pedido (enviado|entregado|confirmado)|"
    r"tu (paquete|envio) (fue |ha sido |esta )?(entregado|enviado|en camino)|fue entregado|tu reembolso|reembolso (en proceso|aprobado|emitido)|"
    r"devolucion (recibida|aprobada|en proceso)|your order (has been |was |is )?(confirmed|shipped|delivered|on its way)|"
    r"has (been )?(shipped|delivered)|your refund)"
)
ORDER_ACTION_RE = re.compile(
    r"(rechazad|declined|actualiza|update your|cancelaremos|will be cancel|recoge|recoger|pick ?up|tienes hasta|"
    r"antes del|a mas tardar|paga|pague|pay now|confirma|confirm)"
)
CARD_CHARGE_RE = re.compile(
    r"(cargo (realizado|aplicado|por)|se realizo un cargo|compra (realizada|aprobada) con tu tarjeta|cargo .{0,30}tarjeta|"
    r"charge (of|was made|was posted)|a charge .{0,40}card|purchase (on|with) your card|card was charged)"
)
RESULTS_RE = re.compile(r"(resultados (ya )?(estan |estan listos|listos|disponibles)|tus resultados|results are (ready|available)|your (test )?results)")
AUTO_RENEW_RE = re.compile(r"(se renovara automaticamente|renovacion automatica|renovara el|will (auto-?)?renew|auto-?renew|renews automatically)")
# Política de renovaciones (post lote 3): renovación YA realizada = informativa, sin tarea de pago.
RENEWED_RE = re.compile(
    r"(se renovo (correctamente|automaticamente|con exito|exitosamente)?|(tu|su) (suscripcion|plan|membresia) (fue|ha sido) renovad|"
    r"renovacion (realizada|exitosa|completada|confirmada)|(was|has been) (successfully )?renewed|renewed successfully|"
    r"renewal (was )?(successful|complete|confirmed))"
)
# Política de facturas (post lote 3): documento ya pagado, domiciliado o sin saldo → solo informativo.
BILL_SETTLED_RE = re.compile(
    r"(pagad[oa]|liquidad[oa]|saldo (actual|pendiente)?:? ?\$?0(\.00)?\b|sin saldo|no (tienes|hay) saldo|domiciliad|cargo automatico|"
    r"se cargara automaticamente|no (se requiere|requiere|necesitas)[^.\n]{0,30}(pago|accion)|paid in full|no payment (is )?(due|required)|"
    r"autopay|automatic payment|comprobante|recibo de pago|payment receipt)"
)
# Política de pagos (post lote 3): un pago ANTERIOR nunca es evidencia de pago de un documento nuevo.
PREVIOUS_PAYMENT_RE = re.compile(
    r"(pago anterior|pagos anteriores|(tu|su) ultimo pago|periodo anterior|previous payment|prior payment|last payment|"
    r"previous (bill|invoice|statement))"
)
# Política de seguridad (post lote 3): tipo, prioridad y tarea van por separado.
SECURITY_STATE_RE = re.compile(
    r"(cuenta (comprometida|bloqueada|suspendida|restringida)|(bloqueamos|hemos bloqueado|suspendimos|restringimos) (tu |su )?(cuenta|acceso)|"
    r"acceso (bloqueado|no autorizado)|account (has been |was |is )?(compromised|locked|suspended|restricted)|"
    r"(we )?(have )?(locked|suspended|restricted) your account|unauthorized (access|sign-?in|login)|"
    r"alguien (conoce|tiene|uso) tu contrasena|someone (knows|has|used) your password)"
)
SECURITY_CHECK_RE = re.compile(
    r"(si no (fuiste|eras) tu|if (this )?(wasn'?t|was not) you|if you didn'?t)[^.\n]{0,80}"
    r"(protege|revisa|verifica|cambia|restablece|asegura|secure|review|check|change|reset)"
)
SECURITY_URGENT_RE = re.compile(
    r"(inmediat|urgente|de inmediato|cuanto antes|hoy mismo|immediately|right away|urgent|as soon as possible|"
    r"\bahora\b|\bnow\b|within \d+ (hours|minutes)|en las proximas? \d+ (horas|minutos))"
)
SECURITY_RISK_RE = re.compile(
    r"(comprometid|compromised|acceso no autorizado|unauthorized|alguien (conoce|tiene|uso) tu contrasena|"
    r"someone (knows|has|used) your password|fraude|fraud|cargo no reconocido|unrecognized (charge|transaction)|"
    r"datos (expuestos|filtrados)|data breach|filtracion)"
)
# Un remitente que pide credenciales o datos no es confiable para abrir un caso de seguridad.
CREDENTIAL_ASK_RE = re.compile(
    r"((comparte|envia|enviar|escribe|ingresa|confirma|proporciona|share|send|enter|provide|confirm)[^.\n]{0,30}"
    r"(contrasena|password|nip|\bpin\b|cvv|clave|codigo|code|datos bancarios|bank details|tarjeta|card number)|"
    r"verifica(r)? tu identidad[^.\n]{0,40}(enlace|link|liga)|verify your identity[^.\n]{0,40}(link|below|here)|"
    r"(enlace|link|liga)[^.\n]{0,40}verif)"
)
# A9 (Etapa 1.2): cita reprogramada → actualiza la cita existente con la nueva fecha explícita.
APPT_RESCHEDULE_RE = re.compile(
    r"((cita|appointment|consulta).{0,60}(reprogramad|rescheduled|reagendad|cambiada (al|para))|"
    r"(reprogramamos|reagendamos|rescheduled) (tu |su |your )?(cita|appointment|consulta))"
)
# A8 (Etapa 1.2): correo saliente que deja al usuario esperando algo con fecha.
WAIT_RE = re.compile(
    r"(quedo (en espera|atento|atenta|pendiente) (de|a) (su|tu|la|el)|quedo (en espera|atento|pendiente) de|quedamos (en espera|atentos|pendientes) de|en espera de (su|tu)|"
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
    r"(factura|fatura|facture|cfdi|recibo|invoice|\bbill\b|estado de cuenta|statement|\bcargo\b|cobro|cobranza|adeudo|saldo|"
    r"aviso de pago|mensualidad|colegiatura|predial|pedido|order|orden)"
)
# --- Post lote 4 (dictamen ASTRA) -------------------------------------------------------------
# 1. Seguridad: señales de riesgo comprobado (compromiso, fraude, acceso no autorizado) ganan a legacy_info/legacy_notice.
RISK_STRONG_RE = re.compile(
    r"(posible fraude|fraude (detectado|en (tu|su) (tarjeta|cuenta))|actividad fraudulenta|suspected fraud|fraud alert|"
    r"cargo no reconocido|compra (inusual|sospechosa|no reconocida)|(operacion|transaccion|movimiento) (inusual|sospechos[oa]|no reconocid[oa])|"
    r"unusual (purchase|transaction)|unrecognized (charge|transaction)|"
    r"cuenta (fue |ha sido |podria estar |puede estar |esta )?comprometida|account (may be |was |has been |is )?compromised|"
    r"acceso no autorizado|unauthorized (access|sign-?in|login|transaction))"
)
PASSWORD_CHANGED_RE = re.compile(
    r"(contrasena|password|clave de acceso)\b[^.\n]{0,20}?\b(fue |ha sido |se ha |was |has been )?"
    r"(modificad|cambiad|actualizad|restablecid|changed|updated|reset)"
)
NOT_YOU_RE = re.compile(
    r"(si no (fuiste|eras) tu|si no (realizaste|hiciste|solicitaste|autorizaste|reconoces) (este|esta|ese|esa|el|la|dicho)|"
    r"if (this )?(wasn'?t|was not) you|if you (didn'?t|did not) (make|request|do|authorize))"
)
NEGATED_SHARE_RE = re.compile(r"(no|nunca|never|don'?t|do not) (compartas|compartir|share|envies|reveles)[^.\n]{0,40}")
# Enlace + petición de escribir contraseña o código → posible phishing (revisión), nunca alerta legítima.
LINK_RE = re.compile(r"(enlace|\blink\b|\bliga\b|haz clic|da clic|\bclick\b|boton|button)")
CRED_ENTRY_RE = re.compile(
    r"\b(introduce|introducir|ingresa|ingresar|escribe|escribir|captura|capturar|proporciona|proporcionar|comparte|"
    r"enter|type|provide|share|submit)\b[^.\n]{0,15}?\b(contrasena|password|codigo|code|nip|pin|cvv|clave)\b"
)
# 2. Facturas: pagada o saldo cero nunca abre obligación.
BILL_PAID_RE = re.compile(
    r"(pagad[oa]\b|liquidad[oa]\b|saldo( actual| pendiente| a pagar)?:? ?\$? ?0(\.00)?\b|sin saldo|no (tienes|hay) saldo|"
    r"paid in full|has been paid|was paid|balance( due)?:? ?\$? ?0(\.00)?\b|zero balance)"
)
BILL_UNPAID_RE = re.compile(r"(no (ha sido |esta |fue )?pagad|sin pagar|unpaid|not (been )?paid)")
# "Total a pagar $X" es una etiqueta del documento, no una exigencia de pago.
PAY_LABEL_RE = re.compile(r"\b(total|monto|importe|cantidad|saldo) (a|por) pagar\b|\bamount payable\b")
# 4. Reservas: no firmes (cotización, lista de espera, sin confirmar) y cancelaciones de reservas o eventos.
BOOKING_CONTEXT_RE = re.compile(
    r"(vuelo|flight|hotel|habitacion|hospedaje|reserva|reservacion|booking|reservation|evento|event|entrada|boleto|ticket|mesa|itinerario)"
)
BOOKING_PENDING_RE = re.compile(
    r"(cotizacion de (vuelo|viaje|hotel|hospedaje|reserva)|propuesta de (vuelo|viaje|itinerario|hospedaje)|lista de espera|waitlist|"
    r"waiting list|no (esta|estan|ha sido|fue) confirmad|not (yet )?confirmed|revisando (la )?disponibilidad|checking availability|"
    r"te avisaremos si (queda|hay|se libera))"
)
BOOKING_CANCEL_RE = re.compile(
    r"(entradas?|boletos?|reserva|reservacion|vuelo|evento|hospedaje|tickets?|booking|reservation|flight|event)\b[^.\n]{0,60}"
    r"(cancelad|cancelled|canceled)"
)
SUBSCRIPTION_RE = re.compile(r"(suscripcion|subscription|membresia|membership|\bplan\b)")
BOOKING_REF_RE = re.compile(r"\b(reserva|reservacion|codigo|localizador|confirmacion|booking|pnr|vuelo|flight)\s*(#|no\.?|:)?\s*[a-z]{0,4}\d[a-z0-9-]*")
# 5. Renovaciones: próxima (con fecha → caso con vencimiento), realizada (aviso) y datos de facturación pendientes (caso).
RENEW_UPCOMING_RE = re.compile(
    r"(se renovara|renovara (automaticamente )?el|proxima renovacion|will (auto-?)?renew|renews on|next renewal)"
)
RENEWAL_ACTION_RE = re.compile(
    r"(actualiza(r)? (tus |tu |los |sus |su )?(datos|informacion|metodo) de (facturacion|pago)|update (your )?(billing|payment) (details|information|method)|"
    r"metodo de pago (vencido|rechazado|expirado)|payment method (expired|declined|failed)|"
    r"(periodo|prueba) (gratuit[oa]|de prueba) (termino|ha terminado|finalizo|vencio|expiro)|(free )?trial (has )?(ended|expired))"
)
# 6. Pedidos, compras y alertas de disponibilidad: avisos visibles con regla propia (antes caían en "ambiguous").
PURCHASE_RE = re.compile(
    r"(confirmacion de (tu |su )?compra|compra (realizada|confirmada|exitosa)|order confirmation|purchase confirmation|"
    r"thanks? (you )?for your (order|purchase))"
)
STOCK_RE = re.compile(r"(vuelve a estar disponible|de nuevo disponible|ya (esta|se encuentra) disponible|back in stock|available again)")
STOCK_ASKED_RE = re.compile(r"(que consultaste|que solicitaste|que te interesa|que seguias|tu alerta|lista de deseos|you (asked|requested)|your alert|wishlist)")
REQUEST_EXTRA_RE = re.compile(
    r"((puedes|podrias|pueden|podrian) (revisar|firmar|enviarme|mandarme|compartirme|confirmarme|decirme|ayudarme)|"
    r"\bavisame\b|me avisas|confirmame|dime (que|si|cuando|a que)|let me know|(could|can) you (review|sign|check))"
)
EVENT_NOUN_RE = re.compile(
    r"(\breunion\b|\bjunta\b|\bmeeting\b|\bcita\b|appointment|\bvuelo\b|\bflight\b|\bdeparts?\b|check-?in|"
    r"\bhotel\b|\breservacion\b|\breserva\b|\bbooking\b|\breservation\b|\bconcierto\b|\bconcert\b|\bevento\b|"
    r"\bevent\b|\bfuncion\b|\bboarding\b|pase de abordar|\bmesa para\b|\bte esperamos\b|\bconferencia\b|\bcongreso\b|"
    # L7reg1 (6): "X se realizará el <fecha>", festival (es/fr/pt).
    r"\bse realizara\b|\btendra lugar\b|\baura lieu\b|\bsera realizad[ao]\b|\bfestival\b)"
)
EVENT_TRAVEL_RE = re.compile(
    r"(\bvuelo\b|\bflight\b|\bdeparts?\b|check-?in|\bhotel\b|\bhospedaje\b|\bboarding\b|pase de abordar|"
    r"\bconcierto\b|\bconcert\b|\bboletos?\b|\btickets?\b|\bmesa para\b|\brestaurante\b|\bfuncion\b)"
)
# Fecha escrita (no relativa): ISO, dd/mm/aaaa, "9 de noviembre", "December 19".
EXPLICIT_DATE_RE = re.compile(
    r"(\b20\d{2}-\d{1,2}-\d{1,2}\b|\b\d{1,2}[/.]\d{1,2}[/.](20)?\d{2}\b|\b\d{1,2} de [a-z]{3,}|"
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.? \d{1,2}\b|\b\d{1,2} (jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b)"
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
    severity: str | None = None
    area: str | None = None  # taxonomía v2: trabajo|hogar|dinero|compras|salud|viajes|promociones; None = Por revisar
    area_tags: list[str] = field(default_factory=list)
    area_v1: str | None = None  # área de la taxonomía v1 (16 áreas), solo trazabilidad
    security_flag: str | None = None  # señal transversal N1/N2; Seguridad nunca es área
    security_tags: list[str] = field(default_factory=list)
    phishing_signals: list[str] = field(default_factory=list)
    area_review_reason: str | None = None
    content_key: str | None = None
    duplicate_of: str | None = None
    duplicate_case_id: str | None = None
    ref_key: str | None = None  # marca + folio/pedido: vincula correos relacionados (pedido → envío → reembolso)
    related_to: str | None = None
    text_normalized: bool = False  # la clasificación salió del texto normalizado (faltas, homoglifos)

    def signals(self) -> dict[str, Any]:
        return {
            "brain_version": BRAIN_VERSION, "rule": self.rule, "protected": self.protected,
            "doc_key": self.doc_key, "key_source": self.key_source if self.doc_key else None, "amount": self.amount, "confidence": self.confidence,
            "suppressed": self.suppressed, "bulk": self.bulk, "reschedule": self.reschedule,
            "phishing_brand": self.phishing_brand, "triage": self.triage, "severity": self.severity,
            "area": self.area, "area_tags": self.area_tags, "taxonomy": "v2", "area_v1": self.area_v1,
            "security_flag": self.security_flag, "security_tags": self.security_tags,
            "phishing_signals": self.phishing_signals or None, "area_review_reason": self.area_review_reason,
            "content_key": self.content_key, "duplicate_of": self.duplicate_of,
            "ref_key": self.ref_key, "related_to": self.related_to, "text_normalized": self.text_normalized or None,
            "review_reason": self.reason if self.triage == "review" or self.confidence < 0.5 else None,
            **self.dates.as_metadata(),
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


def _decode_body(body: str) -> str:
    """Taxonomía v2 / L6: cuerpos que llegan como MIME sin decodificar (base64 o quoted-printable) o como HTML."""
    import base64
    import binascii
    import quopri

    head = body[:200].lower()
    if "content-transfer-encoding: base64" in head:
        payload = body.split("\n\n", 1)[-1]
        chunk = "".join(line.strip() for line in payload.splitlines() if re.fullmatch(r"[A-Za-z0-9+/=]+", line.strip() or "!"))
        try:
            return base64.b64decode(chunk + "=" * (-len(chunk) % 4), validate=False).decode("utf-8", "replace")
        except (binascii.Error, ValueError):
            return body
    if "content-transfer-encoding: quoted-printable" in head:
        try:
            return quopri.decodestring(body.split("\n\n", 1)[-1].encode("utf-8", "replace")).decode("utf-8", "replace")
        except ValueError:
            return body
    if re.search(r"<(html|body|table|div|p)\b", head):
        from app.utils.html_text import html_to_text

        return html_to_text(body) or body
    return body


def content_key(message: dict[str, Any]) -> str | None:
    """Huella de duplicado: remitente + asunto normalizado + cuerpo normalizado (sin firma de móvil ni espacios)."""
    import hashlib

    from app.services.case_engine import normalize_subject

    body = fold(_decode_body(str(message.get("body_text") or message.get("snippet") or "")))
    body = re.sub(r"(enviado desde mi \w+|sent from my \w+)", " ", body)
    body = re.sub(r"\s+", " ", body).strip()[:2000]
    if len(body) < 12:
        return None  # sin cuerpo útil no se afirma que sea duplicado
    sender = str(message.get("sender") or "").lower().strip()
    subject = normalize_subject(str(message.get("subject") or ""))
    return hashlib.sha256(f"{sender}|{subject}|{body}".encode()).hexdigest()[:32]


_WEAK_RULES = {"ambiguous", "legacy_info", "legacy_notice", "legacy_action"}


def _weak(result: Analysis) -> bool:
    return result.rule in _WEAK_RULES or (result.area is None and result.security_flag is None)


def analyze(message: dict[str, Any], *, user_verified: bool | None = None) -> Analysis:
    """Primera pasada sobre el texto tal cual. Si queda débil (ambiguo, sin área o sin señal), segunda pasada sobre el
    texto normalizado (faltas, homoglifos, invisibles). La segunda solo se adopta si aporta: seguridad que la primera
    no vio, un área donde no había, o una regla específica en vez de una genérica."""
    from app.services.brain_v1.normalize import normalize

    first = _analyze_v2(message, user_verified=user_verified)
    if not _weak(first) and first.security_flag:
        return first
    subject = str(message.get("subject") or "")
    raw_body = _decode_body(str(message.get("body_text") or message.get("snippet") or ""))
    n_subject, n_body = normalize(subject), normalize(raw_body[:6000])
    if n_subject == fold(subject) and n_body == fold(raw_body[:6000]):
        return first
    second = _analyze_v2({**message, "subject": n_subject, "body_text": n_body}, user_verified=user_verified)
    gains_security = bool(second.security_flag) and not first.security_flag
    # Una corrección nunca convierte un correo en publicidad/social: eso solo lo decide el texto original.
    gains_topic = _weak(first) and not _weak(second) and second.rule not in {"promotional", "social", "bulk"}
    if gains_security or gains_topic:
        second.text_normalized = True
        return second
    return first


OVERLONG_CHARS = 10000
_MALFORMED_RE = re.compile("\ufffd|[\x00-\x08\x0b\x0c\x0e-\x1f]")


def input_limit(subject: str, body: str) -> str | None:
    """L7reg1 (1): entradas límite → Por revisar (área None). Nunca se adivina un área para ellas."""
    text = (body or "").strip()
    if len(re.sub(r"\s+", "", text)) < 12:
        return "Correo sin cuerpo útil: revisión."
    if _MALFORMED_RE.search(f"{subject or ''}{text[:3000]}"):
        return "Texto dañado o mal codificado: revisión."
    if len(text) > OVERLONG_CHARS:
        return "Correo demasiado largo para clasificarlo con seguridad: revisión."
    return None


def _analyze_v2(message: dict[str, Any], *, user_verified: bool | None = None) -> Analysis:
    from app.services.brain_v1.phishing_v2 import detect
    from app.services.brain_v1.taxonomy import classify_area
    from app.services.brain_v1.taxonomy_v2 import classify_v2

    raw_body = str(message.get("body_text") or message.get("snippet") or "")
    body = _decode_body(raw_body)
    if body is not raw_body:
        message = {**message, "body_text": body}
    result = _analyze(message, user_verified=user_verified)
    subject = str(message.get("subject") or "")
    sender = str(message.get("sender") or "")
    text = fold(f"{subject}\n{body[:3000]}")
    legacy = classify_area(result.rule, text, sender, result.confidence)
    result.area_v1 = legacy["area"]
    verdict = detect(sender, text)
    phishing = result.rule == "phishing_suspect" or verdict.is_phishing
    # security_unverified ya es un caso visible en revisión (política de seguridad): se conserva; solo cambia el área.
    if verdict.is_phishing and result.rule not in {"phishing_suspect", "security_unverified"}:
        # Marca desconocida: se pasa a revisión; nunca cobro, cita ni área temática.
        result.rule, result.triage, result.actionable = "phishing_suspect", "review", False
        result.confidence = RULE_CONFIDENCE["phishing_suspect"]
        result.reason = "Posible phishing o fraude (" + ", ".join(verdict.signals) + "). No hagas clic ni respondas; revisa."
        result.protected = "security"
        result.severity = "review"
        result.dates = DateResult()
        result.doc_key, result.amount = None, None
    result.phishing_signals = verdict.signals
    info = classify_v2(result.rule, text, sender, result.confidence, phishing=phishing, severity=result.severity,
                       phishing_tags=verdict.tags, triage=result.triage, input_limit=input_limit(subject, raw_body),
                       phishing_signals=verdict.signals)
    result.area, result.area_tags = info["area"], info["tags"]
    result.security_flag, result.security_tags = info["security_flag"], info["security_tags"]
    result.area_review_reason = info["review_reason"]
    if info.get("clear_review"):
        # L8reg1 (4): tema único y explícito → aviso con área, sin marca de revisión.
        result.triage, result.confidence = "notice", max(result.confidence, 0.6)
    if not phishing and not input_limit(subject, raw_body):
        _explicit_phrase_dates(result, subject, body, message.get("received_at"))
    result.content_key = content_key(message)
    from app.services.brain_v1.documents import extract_doc_token

    token = None if phishing else extract_doc_token(subject, body)
    result.ref_key = f"{result.brand}:{token}" if token and result.brand else None
    return result


# L8reg1 (5): frases de fecha explícita que antes se perdían cuando la regla no extrae fechas. Solo fecha ESCRITA
# justo después de la frase (ISO, dd/mm/aaaa o "d de mes"); nunca se infiere una fecha ausente.
_PHRASE_DATES = (
    ("due", re.compile(r"\bpago pactado para (el )?")), ("due", re.compile(r"\bdoit etre reglee? avant (le )?")),
    ("due", re.compile(r"\bantes del ")), ("due", re.compile(r"\bvence em ")), ("event", re.compile(r"\bpaquete (esta |sera )?previsto para (el )?")),
)


def _explicit_phrase_dates(result: Analysis, subject: str, body: str, received: Any) -> None:
    from datetime import datetime, time

    from app.services.brain_v1.dates import MX, _parse_in, received_local

    text = fold(f"{subject}\n{body[:3000]}")
    anchor = received_local(received).date()
    for role, rx in _PHRASE_DATES:
        if (role == "due" and result.dates.due_at) or (role == "event" and result.dates.event_at):
            continue
        values = set()
        for m in rx.finditer(text):
            snippet = text[m.end():m.end() + 40]
            found = [d for d, pos in _parse_in(snippet, anchor, False, explicit_only=True) if pos <= 2]
            values |= {d for d in found if not isinstance(d, str)}
        if len(values) != 1:
            continue  # sin fecha escrita o varias fechas: no se adivina
        value = values.pop()
        if role == "due":
            result.dates.due_at = datetime.combine(value, time(23, 59), MX).isoformat()
            result.dates.due_evidence = text[:240]
        else:
            result.dates.event_at = datetime.combine(value, time(0, 0), MX).isoformat()
            result.dates.event_evidence = text[:240]


def _analyze(message: dict[str, Any], *, user_verified: bool | None = None) -> Analysis:
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

    # Post lote 4 (1): enlace + "introduce tu contraseña/código" → posible phishing en revisión (no aviso legítimo).
    cred_text = NEGATED_SHARE_RE.sub(" ", text)
    if LINK_RE.search(cred_text) and CRED_ENTRY_RE.search(cred_text):
        result = build("phishing_suspect", "review", False,
                       "Posible phishing: pide abrir un enlace y escribir contraseña o código. Revisa sin hacer clic.",
                       protected="security")
        result.severity = "review"
        return result

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
    if not sec and SECURITY_STATE_RE.search(text):
        sec = "security"  # política de seguridad: cuenta comprometida o bloqueada siempre es tipo seguridad
    # Post lote 4 (1): riesgo comprobado o "tu contraseña cambió + si no fuiste tú" siempre es seguridad,
    # aunque el remitente parezca automatizado (nunca legacy_info / legacy_notice).
    risk = bool(RISK_STRONG_RE.search(text))
    pw_check = bool(PASSWORD_CHANGED_RE.search(text) and NOT_YOU_RE.search(text))
    if sec != "code" and (risk or pw_check or PASSWORD_CHANGED_RE.search(text)):
        sec = "security"  # un cambio de contraseña sin "si no fuiste tú" queda como aviso protegido
    if sec == "code" or (sec and not VERIFY_RE.search(text)):
        if sec == "security":
            # Política única de seguridad: el TIPO es "seguridad" (protegido, nunca oculto); la TAREA existe si la
            # cuenta está comprometida/bloqueada o si se pide comprobar actividad; la PRIORIDAD se decide aparte
            # (crítica solo con urgencia explícita + riesgo significativo).
            state = bool(SECURITY_STATE_RE.search(text) or SECURITY_ACTION_RE.search(text)) or risk
            check = bool(SECURITY_CHECK_RE.search(text)) or pw_check
            if (state or check) and CREDENTIAL_ASK_RE.search(NEGATED_SHARE_RE.sub(" ", text)):
                result = build("security_unverified", "review", True,
                               "Alerta de seguridad que pide credenciales o datos por enlace: caso visible en revisión, "
                               "nunca se oculta ni se trata como legítima.",
                               protected=sec)
                result.severity = "review"
                return result
            if state or check:
                urgent = bool(SECURITY_URGENT_RE.search(text)) and bool(SECURITY_RISK_RE.search(text))
                result = build("security_action", "action_required", True,
                               "Alerta de seguridad que requiere tu atención: revisa el acceso a tu cuenta."
                               if state else "Actividad que debes comprobar («si no fuiste tú»): caso visible.",
                               protected=sec)
                # Prioridad según severidad comprobada: crítica = urgencia + riesgo; riesgo (compromiso/fraude) = alta;
                # bloqueo o comprobación = normal.
                result.severity = "critical" if urgent else ("risk" if risk else ("compromise" if state else "check"))
                return result
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

    if RENEWAL_ACTION_RE.search(text):
        # Post lote 4 (5): datos de facturación pendientes o prueba terminada → caso (sin fecha si no está escrita).
        return build("renewal_action", "action_required", True,
                     "Suscripción que necesita una acción tuya (datos de facturación, método de pago o fin de prueba).",
                     kind="renewal", protected=prot)

    if PAYMENT_CONFIRM_RE.search(text) and not NEGATED_PAYMENT_RE.search(text) and not PREVIOUS_PAYMENT_RE.search(text):
        rule = "partial_payment" if PARTIAL_RE.search(text) else "payment_confirmation"
        return build(rule, "notice", True, "Confirmación de pago; se busca el caso con el mismo folio.",
                     with_doc=True, protected="invoice")

    if BOOKING_CANCEL_RE.search(text) and not SUBSCRIPTION_RE.search(text) and not APPT_CANCEL_RE.search(text):
        # Post lote 4 (4): cancelación de reserva/evento → actualiza el caso existente (misma fecha), nunca otro.
        return build("booking_cancel", "notice", True, "Cancelación de reserva o evento; actualiza la reserva existente.",
                     kind="appointment_cancel", protected=prot)
    if BOOKING_CONTEXT_RE.search(text) and BOOKING_PENDING_RE.search(text) and not PAY_DEMAND_RE.search(PAY_LABEL_RE.sub(" ", text)):
        # Post lote 4 (4): cotización, lista de espera o reserva sin confirmar → aviso, nunca compromiso.
        return build("booking_pending", "notice", False,
                     "Reserva no confirmada (cotización, lista de espera o pendiente): aviso, sin compromiso.", protected=prot)
    if APPT_CANCEL_RE.search(text):
        return build("appointment_cancel", "notice", True, "Cancelación de cita; actualiza la cita existente.",
                     kind="appointment_cancel", protected=prot)
    if APPT_RESCHEDULE_RE.search(text):
        analysis = build("appointment", "notice", True, "Cita reprogramada: se actualiza la fecha de la cita.",
                         kind="appointment", protected=prot or "health")
        analysis.reschedule = True
        if analysis.dates.event_at:
            return analysis
    automated = _sender_is_automated(sender) or bool(TRANSACTIONAL_LOCALS.match(sender_email.split("@")[0].lower()))
    # Post lote 4 (4): un remitente no automatizado cuenta si trae código de reserva (nunca solo por el asunto).
    firm_source = automated or bool(BOOKING_REF_RE.search(text))
    if BOOKING_RE.search(text) and firm_source and not BOOKING_NOT_FIRM_RE.search(text):
        # A12: confirmación automática con fecha explícita → compromiso programado. Nunca para correos de personas.
        booking = build("booking", "notice", True, "Confirmación automática de reservación, itinerario o registro.",
                        kind="booking", protected=prot)
        if booking.dates.event_at:
            return booking
    if APPT_RE.search(text):
        analysis = build("appointment", "action_required", True, "Cita confirmada: compromiso con fecha.",
                         kind="appointment", protected=prot or "health")
        if not analysis.dates.event_at:
            analysis.rule, analysis.triage, analysis.actionable = "ambiguous", "review", False
            analysis.confidence = 0.4
            analysis.reason = "Cita sin fecha clara; requiere revisión."
        return analysis

    demand_text = PAY_LABEL_RE.sub(" ", text)  # Post lote 4 (2): "total a pagar" no es exigencia
    # Fix event_at: reunión, junta, cita, vuelo, hotel, reserva o evento con FECHA EXPLÍCITA (nunca relativa) → compromiso
    # programado (event_at, distinto de due_at). Sin fecha explícita sigue el flujo normal.
    if (EVENT_NOUN_RE.search(text) and not PAY_DEMAND_RE.search(demand_text) and not PROMO_RE.search(text)
            and not BOOKING_NOT_FIRM_RE.search(text) and not BOOKING_PENDING_RE.search(text)):
        travel = bool(EVENT_TRAVEL_RE.search(text))
        event = build("booking" if travel else "appointment", "notice" if travel else "action_required", True,
                      "Evento con fecha explícita (reunión, cita, vuelo, hospedaje o reserva).",
                      kind="booking" if travel else "appointment", protected=prot)
        if event.dates.event_at and EXPLICIT_DATE_RE.search(fold(event.dates.event_evidence or "")):
            return event
    if automated and not PAY_DEMAND_RE.search(demand_text):
        # A13: plantillas automáticas que solo informan.
        if ORDER_NOTICE_RE.search(text) and not ORDER_ACTION_RE.search(text):
            return build("auto_notice", "informational", False, "Aviso automático de pedido, envío, entrega o reembolso.",
                         protected=prot)
        if CARD_CHARGE_RE.search(text):
            return build("auto_notice", "notice", False, "Cargo con tarjeta: aviso protegido del banco.", protected="bank")
        if RESULTS_RE.search(text):
            return build("auto_notice", "notice", False, "Resultados disponibles: aviso de salud.", protected="health")
        if RENEWED_RE.search(text) and not PAY_DEMAND_RE.search(text):
            return build("auto_notice", "notice", False, "Renovación ya realizada: aviso informativo, sin tarea de pago.",
                         protected=prot)
        if AUTO_RENEW_RE.search(text) and not RENEW_UPCOMING_RE.search(text):
            return build("auto_notice", "notice", False, "Renovación automática: aviso, sin pendiente.", protected=prot)

    identity = identify_sender(sender) or {}
    vertical = str(identity.get("vertical") or "")
    is_social = bool(social_platform(sender)) or vertical == "social" or SOCIAL_LABEL in labels
    if is_social:
        return build("social", "social", False, "Notificación de red social sin acción.")

    marketing = (
        PROMO_LABEL in labels or _sender_is_promotional(sender) or is_marketing_local_part(sender)
        or bool(PROMO_RE.search(text))
    )
    demand = bool(PAY_DEMAND_RE.search(demand_text))
    invoice_term = bool(INVOICE_TERM_RE.search(text))
    promo_terms = bool(PROMO_RE.search(text))

    if invoice_term and BILL_PAID_RE.search(text) and not BILL_UNPAID_RE.search(text):
        # Post lote 4 (2): factura pagada o saldo $0 → aviso; nunca abre obligación.
        return build("bill_settled", "notice", False, "Factura pagada o sin saldo: aviso, no crea pendiente.",
                     protected="invoice")
    if RENEW_UPCOMING_RE.search(text) and not marketing:
        # Post lote 4 (5): renovación próxima con fecha escrita → caso con vencimiento; sin fecha → aviso.
        upcoming = build("renewal_upcoming", "action_required", True, "Renovación próxima con fecha y cobro.",
                         kind="renewal", protected=prot)
        if upcoming.dates.due_at and extract_amount(subject, body) is not None:
            return upcoming  # fecha + importe escritos = cobro próximo
        return build("auto_notice", "notice", False, "Renovación automática sin fecha o sin importe escritos: aviso, sin pendiente.",
                     protected=prot)
    if RENEWED_RE.search(text) and not demand and not marketing:
        return build("renewal_done", "notice", False, "Renovación ya realizada: aviso informativo, sin tarea de pago.",
                     protected=prot)
    if (ORDER_NOTICE_RE.search(text) and not ORDER_ACTION_RE.search(text) or PURCHASE_RE.search(text)) and not demand and not marketing:
        return build("order_notice", "notice", False, "Aviso de compra, pedido, envío o entrega; no crea pendiente.",
                     protected=prot)
    # C3: factura o cobro que pide pago → accionable aunque el remitente sea desconocido.
    if demand and invoice_term and not promo_terms:
        rule = "invoice_due" if re.search(r"(factura|fatura|facture|cfdi|recibo|invoice|\bbill\b|estado de cuenta|statement)", text) else "charge_due"
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
    if (REQUEST_RE.search(text) or REQUEST_EXTRA_RE.search(text)) and not _sender_is_automated(sender):
        return build("request", "action_required", True, "Solicitud directa de una persona.", with_doc=True,
                     protected=prot)

    if (invoice_term and re.search(r"(factura|cfdi|recibo|invoice|estado de cuenta|statement)", text)
            and automated and not BILL_SETTLED_RE.search(text) and extract_amount(subject, body)):
        # Política de facturas (post lote 3): factura con importe y sin vencimiento escrito → caso de seguimiento
        # en revisión, SIN fecha límite (nunca se infiere del fin del periodo).
        followup = _with_period(build("bill_followup", "review", True,
                                      "Factura con importe y sin fecha límite escrita: seguimiento en revisión, sin vencimiento.",
                                      with_doc=True, protected="invoice"), subject, body, received)
        followup.dates.due_at = None
        followup.dates.due_evidence = None
        return followup
    if invoice_term and re.search(r"(factura|cfdi|recibo|invoice|estado de cuenta|statement)", text):
        return build("invoice_info", "notice", False, "Comprobante o estado de cuenta informativo, sin cobro pendiente.",
                     protected=prot)

    if STOCK_RE.search(text) and STOCK_ASKED_RE.search(text):
        return build("stock_alert", "notice", False, "Alerta de disponibilidad que pediste: aviso, sin pendiente.")

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
