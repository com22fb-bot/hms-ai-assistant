"""Rule-based insights for one email (no AI, no network, no writes).

``build_insight`` reads a stored message (subject, sender, body_text,
body_html) and returns:

* ``kind``      – event type (payment_declined, bill_due, debt_overdue, …)
* ``area``      – Núcleo life area derived from the kind (or ``None``)
* ``facts``     – amounts, dates/deadline, merchant, reference, card ending,
                  brand: every value is copied from the email text
* ``main_idea`` – one sentence per UI language (es/en/fr/it/pt) built only
                  from ``facts`` and fixed template words
* ``excerpts``  – 1–3 sentences copied verbatim; ``verified_excerpts``
                  guarantees each one is an exact substring of the cleaned
                  text (``clean.text``)
* ``preview``   – cleaned one-line preview

Everything is deterministic: same input, same output.
"""

from __future__ import annotations

import re
import unicodedata
from email.utils import parseaddr
from typing import Any, Callable

from app.utils.mail_clean import CleanEmail, clean_email, clean_subject, preview_text, strip_subject_prefix

INSIGHT_VERSION = "insights-v1"
LANGS = ("es", "en", "fr", "it", "pt")
MAX_EXCERPTS = 3


def fold(value: str) -> str:
    text = unicodedata.normalize("NFD", value or "")
    return "".join(ch for ch in text if not unicodedata.combining(ch)).lower()


# ---------------------------------------------------------------- facts

_AMOUNT = re.compile(
    r"(?:(?:MXN|MX\$|US\$|USD|EUR|€)\s?\$?\s?|\$\s?)\d[\d,]*(?:\.\d{1,2})?(?:\s?(?:M\.N\.|MXN|USD))?"
    r"|\b\d{1,3}(?:,\d{3})*(?:\.\d{2})\s?(?:M\.N\.|MXN|pesos|USD|d[oó]lares)",
)
_AMOUNT_LABELS = (
    ("pago requerido", 9), ("pago minimo", 9), ("total a pagar", 9), ("monto a pagar", 9), ("importe total", 8),
    ("monto de rechazo", 8), ("amount due", 8), ("liquidar", 7), ("liquide", 7), ("importe", 6), ("monto", 6),
    ("total", 5), ("saldo", 5), ("cargo", 5), ("pago de", 5), ("amount", 5), ("recibiste", 5), ("deuda", 3),
)
_MONTHS_ES = "enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre"
_MONTHS_EN = (
    "january|february|march|april|may|june|july|august|september|october|november|december"
    "|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec"
)
_DATE = re.compile(
    r"\b\d{1,2}/(?:\d{1,2}|[A-Za-z]{3,4})/\d{2,4}\b"
    r"|\b\d{4}-\d{2}-\d{2}\b"
    rf"|\b\d{{1,2}} de (?:{_MONTHS_ES})(?: de(?:l)? \d{{4}})?\b"
    rf"|\b(?:{_MONTHS_EN})\.? \d{{1,2}}(?:, \d{{4}})?\b"
    rf"|\b\d{{1,2}} (?:{_MONTHS_EN}) \d{{4}}\b",
    re.IGNORECASE,
)
_DUE_CUE = re.compile(
    r"(?:vence|vencen|vencimiento|fecha l[ií]mite|antes del|a m[aá]s tardar|pagar antes|due|expira|caduca|liquide.{0,40}el|hasta el)",
    re.IGNORECASE,
)
_MERCHANT_LABEL = re.compile(
    r"(?:establecimiento|comercio|merchant|tienda|negocio)\s*:\s*(.{2,80})", re.IGNORECASE
)
_MERCHANT_STOP = re.compile(
    r"\s+(?:evita|fecha|monto|tarjeta|importe|hora|referencia|consulta|contact)\b.*$", re.IGNORECASE
)
_MERCHANT_SUBJECT = re.compile(r"pago no autorizado para\s+(.{2,60})$", re.IGNORECASE)
_REFERENCE = re.compile(
    r"(?:n\.?\s?[ºo°]\s?de referencia|n[uú]mero de referencia(?: de [A-Za-z]+)?|referencia|folio(?:/expediente)?"
    r"|clave de rastreo|n[uú]mero de gu[ií]a|tracking number|order (?:no\.?|number|#)|pedido (?:no\.?|#)"
    r"|pr[eé]stamo personal n[uú]mero)\s*[:#]?\s*([A-Z0-9][A-Z0-9-]{4,})",
    re.IGNORECASE,
)
_CARD = re.compile(r"(?:terminaci[oó]n|termina en|ending in|\*{2,}|x{3,})\s*(\d{4})\b", re.IGNORECASE)

# Display names for senders whose address does not say who they are.
_BRAND_BY_DOMAIN = {
    "bazdigital.com": "Banco Azteca",
    "bancoazteca.com.mx": "Banco Azteca",
    "cfe.mx": "CFE",
    "issste.gob.mx": "ISSSTE",
    "cleverbridge.com": "Cleverbridge",
    "bbva.mx": "BBVA",
    "bbva.com": "BBVA",
    "santander.com.mx": "Santander",
    "banamex.com": "Banamex",
    "mercadolibre.com.mx": "Mercado Libre",
    "mercadolibre.com": "Mercado Libre",
    "mercadopago.com.mx": "Mercado Pago",
    "accounts.google.com": "Google",
    "accountprotection.microsoft.com": "Microsoft",
    "cc.yahoo.com": "Yahoo",
    "indeed.com": "Indeed",
    "totalplay.com.mx": "Totalplay",
    "telcel.com": "Telcel",
    "amazon.com.mx": "Amazon",
    "amazon.com": "Amazon",
}
_PERSONAL_DOMAINS = {
    "gmail.com", "yahoo.com", "yahoo.com.mx", "hotmail.com", "outlook.com", "live.com", "live.com.mx",
    "icloud.com", "me.com", "prodigy.net.mx", "aol.com", "protonmail.com", "proton.me",
}
_MARKETING_SUBDOMAIN = re.compile(
    r"^(?:email|e|em|hola|mail|mails|prom|promo|promociones|campaign|news|newsletter|marketing|info|ofertas|mkt|envio|envios|boletin|noticias|comunicacion|comunicados)\.",
    re.IGNORECASE,
)
_NOREPLY = re.compile(r"(?:no-?reply|noreply|no_reply|notificacion|notification|alert|aviso|mailer|info@|news)", re.IGNORECASE)


def _sender_parts(sender: str | None) -> tuple[str, str, str]:
    name, address = parseaddr(str(sender or ""))
    address = address.lower()
    domain = address.split("@", 1)[1] if "@" in address else ""
    return name.strip().strip('"'), address, domain


def _registered_domain(domain: str) -> str:
    for known in _BRAND_BY_DOMAIN:
        if domain == known or domain.endswith("." + known):
            return known
    return domain


def brand_for(sender: str | None) -> str:
    name, address, domain = _sender_parts(sender)
    known = _registered_domain(domain)
    if known in _BRAND_BY_DOMAIN:
        return _BRAND_BY_DOMAIN[known]
    clean_name = re.sub(r"\s+", " ", clean_subject(name)).strip()
    if clean_name and "@" not in clean_name and len(clean_name) <= 48:
        return clean_name
    if domain:
        parts = [p for p in domain.split(".") if p not in {"com", "mx", "net", "org", "gob", "edu", "co", "www", "mail", "email", "e", "info"}]
        if parts:
            label = parts[-1]
            return label.upper() if len(label) <= 4 else label.capitalize()
    return ""


def _clean_amount(raw: str) -> str:
    return raw.strip().rstrip(",.") if not raw.strip().endswith("M.N.") else raw.strip()


def extract_facts(subject: str, clean: CleanEmail, sender: str | None) -> dict[str, Any]:
    text = clean.text
    lines = clean.lines
    amounts: list[str] = []
    scored: list[tuple[int, int, str]] = []
    for line_index, line in enumerate(lines):
        folded = fold(line)
        for match in _AMOUNT.finditer(line):
            raw = _clean_amount(match.group(0))
            if not re.search(r"\d", raw) or raw in amounts:
                continue
            amounts.append(raw)
            prefix = folded[max(0, match.start() - 40):match.start()]
            weight = max((w for label, w in _AMOUNT_LABELS if label in prefix), default=1)
            scored.append((-weight, line_index, raw))
    for match in _AMOUNT.finditer(subject):
        raw = _clean_amount(match.group(0))
        if raw not in amounts:
            amounts.append(raw)
            scored.append((-4, -1, raw))
    amount = sorted(scored)[0][2] if scored else None

    dates: list[str] = []
    due_date: str | None = None
    for source in (text, subject):
        for match in _DATE.finditer(source):
            raw = match.group(0)
            if raw not in dates:
                dates.append(raw)
            window = source[max(0, match.start() - 60):match.start()]
            if due_date is None and _DUE_CUE.search(window):
                due_date = raw

    merchant = None
    for line in lines:
        found = _MERCHANT_LABEL.search(line)
        if found:
            value = _MERCHANT_STOP.sub("", found.group(1)).strip(" .,:;")
            value = re.sub(r"(?:\s+[+\d][\d\s+-]{3,})+$", "", value).strip(" .,")
            if value:
                merchant = value
                break
    if merchant is None:
        found = _MERCHANT_SUBJECT.search(subject)
        if found:
            merchant = found.group(1).strip(" .,")

    reference = None
    for source in (subject, text):
        found = _REFERENCE.search(source)
        if found:
            reference = found.group(1)
            break
    card = _CARD.search(text)
    return {
        "brand": brand_for(sender),
        "amount": amount,
        "amounts": amounts[:6],
        "due_date": due_date,
        "date": dates[0] if dates else None,
        "dates": dates[:6],
        "merchant": merchant,
        "reference": reference,
        "card_last4": card.group(1) if card else None,
    }


# ---------------------------------------------------------------- kinds

_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("payment_declined", re.compile(r"rechazo por saldo|saldo insuficiente|pago no (?:ha sido )?autorizado|su pago no ha sido autoriza|pago rechazado|pago declinado|compra rechazada|cargo rechazado|payment (?:was )?declined|card (?:was )?declined|payment failed|no pudimos (?:procesar|cobrar)|could not process your payment")),
    ("verification_code", re.compile(r"codigo de (?:un solo uso|seguridad|verificacion|acceso)|one[- ]time (?:code|passcode|password)|verification code|security code|\btu codigo\b|your code")),
    ("magic_link", re.compile(r"sign-?in link|enlace (?:seguro|para iniciar sesion|de acceso)|link to sign in|reset your (?:\w+ )?password|restablece\w* tu contrasena|olvidaste tu contrasena|confirma tu correo|verifica tu (?:direccion de )?correo|verify your email")),
    ("security_alert", re.compile(r"alerta de seguridad|security alert|nuevo inicio de sesion|inicio de sesion|new sign[- ]?in|contrasena de aplicacion|app password|verificacion en dos pasos|two-step|2-step|se cambio la contrasena|password (?:was )?changed|informacion de seguridad|aplicaciones conectadas|actividad (?:inusual|sospechosa)|unusual activity|dispositivo de confianza")),
    ("card_status", re.compile(r"entregar tu tarjeta|tu tarjeta (?:ya )?(?:esta|va) en camino|tarjeta.{0,40}(?:devuelta|en camino)|directo a tus manos|activa tu tarjeta")),
    ("debt_offer", re.compile(r"liquidar (?:solo )?con|liquide (?:su cuenta )?(?:solo )?con|descuento (?:especial )?para liquidar|liquidar su credito con un descuento|maximo descuento")),
    ("debt_overdue", re.compile(r"saldo vencido|pago vencido|adeudo que presenta|al corriente|cobranza|extrajudicial|estatus actual de su credito|solucione su tarjeta|deuda total")),
    ("bill_due", re.compile(r"aviso de cobro|aviso de factura|aviso recibo|tu aviso|recibo (?:de luz|disponible|digital)|fecha limite de pago|adeudo|monto a pagar|total a pagar|saldo a pagar|formato de pago|\bfopi\b|payment due|amount due|bill is (?:ready|due)|\bvencen? el\b")),
    ("order_delivered", re.compile(r"llego tu compra|fue entregad|ha sido entregad|pedido entregado|paquete entregado|was delivered|has been delivered")),
    ("order_shipped", re.compile(r"\ben camino\b|fue enviad|ha sido enviad|out for delivery|\bshipped\b|on its way|numero de guia|tracking number")),
    ("order_placed", re.compile(r"\bcompraste\b|gracias por tu compra|confirmacion de (?:tu )?(?:pedido|compra)|pedido confirmado|order confirm|thanks for your order")),
    ("transfer_received", re.compile(r"recibiste (?:un pago|una transferencia|dinero|un deposito)|deposito recibido|te enviaron|you received a payment")),
    ("transfer_sent", re.compile(r"operacion spei|\bspei\b|transferencia (?:enviada|realizada)|dinero enviado|\benviaste\b")),
    ("statement", re.compile(r"estado de cuenta|reporte mensual|statement is (?:ready|available)|account statement")),
    ("receipt", re.compile(r"comprobante|\bfactura\b|\bcfdi\b|\bticket\b|resumen de compra|recibo de pago|payment received|pago (?:recibido|aplicado|exitoso)|timbrad")),
    ("terms_update", re.compile(r"(?:terminos y condiciones|condiciones del servicio|politica de privacidad|aviso de privacidad|nuevas condiciones|terms (?:of service|and conditions)|privacy policy|storage fees).{0,80}|(?:actualiz\w*|update\w*|nuevas|conoce).{0,60}(?:terminos|condiciones|privacidad|terms|fees)")),
    ("job", re.compile(r"entrevista|interview|postulacion|vacante|curriculum|\bcv\b|empleo|\bjobs?\b|reclutamiento|recruit")),
    ("promo", re.compile(r"\d+ ?% ?(?:de )?(?:descuento|dto|off|reembolso)|\bdto\b|\boferta|\bpromo|\bcupon|cuponera|preventa|\bmsi\b|meses sin intereses|black friday|hot sale|registrate y recibe|gana dinero|ultimos dias|ultimas \d+ horas|\bbogo\b|when you spend|limited time|ends soon|\bestrena|\bsale\b")),
]

KIND_AREA = {
    "verification_code": "security",
    "magic_link": "security",
    "security_alert": "security",
    "payment_declined": "money",
    "card_status": "money",
    "debt_offer": "money",
    "debt_overdue": "money",
    "bill_due": "bills",
    "order_delivered": "orders",
    "order_shipped": "orders",
    "order_placed": "orders",
    "transfer_received": "money",
    "transfer_sent": "money",
    "statement": "money",
    "receipt": "money",
    "terms_update": "other",
    "job": "work",
    "gov_procedure": "government",
    "promo": "promos",
}


# "Nunca te pediremos tu código de seguridad" is advice, not a code email.
_NEGATED = re.compile(r"(?:nunca|jamas|never|ningun[ao]?|no (?:te |le )?(?:pediremos|solicitaremos|solicitaran|pedira))[^.]*$")


def _is_marketing_domain(domain: str) -> bool:
    """email.brand.com, mx.email.samsung.com, envio.brand.com.mx…"""
    labels = domain.split(".")
    keep = 3 if len(labels) > 2 and labels[-2] in {"com", "co", "gob", "org", "net"} else 2
    return any(_MARKETING_SUBDOMAIN.match(label + ".") for label in labels[:-keep])


def detect_kind(subject: str, clean: CleanEmail, sender: str | None, triage_category: str | None = None) -> str:
    _, address, domain = _sender_parts(sender)
    head = fold(f"{subject}\n{clean.text[:1500]}")
    subject_folded = fold(subject)
    # Codes / links / alerts must be the point of the email, not a line of
    # boilerplate ("nunca te pediremos tu código de seguridad").
    short_head = {
        "verification_code": fold(f"{subject}\n{clean.text[:400]}"),
        "magic_link": fold(f"{subject}\n{clean.text[:400]}"),
        "security_alert": fold(f"{subject}\n{clean.text[:600]}"),
    }
    for kind, pattern in _RULES:
        if kind == "terms_update" and not pattern.search(subject_folded):
            continue
        if kind == "promo":
            break
        scope = short_head.get(kind, head)
        if kind in short_head:
            hit = any(not _NEGATED.search(scope[max(0, m.start() - 80):m.start()]) for m in pattern.finditer(scope))
        else:
            hit = bool(pattern.search(scope))
        if hit:
            # Job boards and job mail mention "empleo" everywhere: only the subject decides.
            if kind == "job" and not pattern.search(subject_folded):
                continue
            return kind
    if domain.endswith(".gob.mx") or domain.endswith(".gov") or domain.endswith(".gob.es"):
        return "gov_procedure"
    promo = dict(_RULES)["promo"]
    if triage_category == "promotional" or promo.search(subject_folded):
        return "promo"
    if domain in _PERSONAL_DOMAINS or (re.match(r"^(?:re|rv|fw|fwd)\s*:", subject_folded) and not _NOREPLY.search(address)):
        return "personal"
    if _is_marketing_domain(domain) or promo.search(head):
        return "promo"
    return "unknown"


# ---------------------------------------------------------------- main idea

def _amt(value: str | None) -> str | None:
    if not value:
        return None
    return re.sub(r"\$\s+", "$", value)


def _topic(subject: str) -> str:
    topic = strip_subject_prefix(clean_subject(subject)) or "—"
    return topic if len(topic) <= 90 else topic[:89].rstrip() + "…"


Vars = dict[str, Any]
Template = Callable[[Vars], str]


def _t(es: Template, en: Template, fr: Template, it: Template, pt: Template) -> dict[str, Template]:
    return {"es": es, "en": en, "fr": fr, "it": it, "pt": pt}


def _opt(value: Any, text: str) -> str:
    return text if value else ""


TEMPLATES: dict[str, dict[str, Template]] = {
    "payment_declined": _t(
        lambda v: f"{v['brand']} rechazó {'el cobro de ' + v['merchant'] if v['merchant'] else 'un pago'}{_opt(v['amount'], ' por ' + str(v['amount']))}{_opt(v['insufficient'], ' por saldo insuficiente')}.",
        lambda v: f"{v['brand']} declined {'the ' + v['merchant'] + ' charge' if v['merchant'] else 'a payment'}{_opt(v['amount'], ' of ' + str(v['amount']))}{_opt(v['insufficient'], ' for insufficient funds')}.",
        lambda v: f"{v['brand']} a refusé {'le prélèvement de ' + v['merchant'] if v['merchant'] else 'un paiement'}{_opt(v['amount'], ' de ' + str(v['amount']))}{_opt(v['insufficient'], ' pour solde insuffisant')}.",
        lambda v: f"{v['brand']} ha rifiutato {'l’addebito di ' + v['merchant'] if v['merchant'] else 'un pagamento'}{_opt(v['amount'], ' di ' + str(v['amount']))}{_opt(v['insufficient'], ' per saldo insufficiente')}.",
        lambda v: f"{v['brand']} recusou {'a cobrança de ' + v['merchant'] if v['merchant'] else 'um pagamento'}{_opt(v['amount'], ' de ' + str(v['amount']))}{_opt(v['insufficient'], ' por saldo insuficiente')}.",
    ),
    "card_status": _t(
        lambda v: f"{v['brand']} no pudo entregar tu tarjeta{_opt(v['card'], ' con terminación ' + str(v['card']))}." if v["failed"] else f"{v['brand']}: tu tarjeta{_opt(v['card'], ' con terminación ' + str(v['card']))} va en camino.",
        lambda v: f"{v['brand']} could not deliver your card{_opt(v['card'], ' ending in ' + str(v['card']))}." if v["failed"] else f"{v['brand']}: your card{_opt(v['card'], ' ending in ' + str(v['card']))} is on its way.",
        lambda v: f"{v['brand']} n’a pas pu livrer votre carte{_opt(v['card'], ' se terminant par ' + str(v['card']))}." if v["failed"] else f"{v['brand']} : votre carte{_opt(v['card'], ' se terminant par ' + str(v['card']))} est en route.",
        lambda v: f"{v['brand']} non è riuscita a consegnare la tua carta{_opt(v['card'], ' che termina con ' + str(v['card']))}." if v["failed"] else f"{v['brand']}: la tua carta{_opt(v['card'], ' che termina con ' + str(v['card']))} è in arrivo.",
        lambda v: f"{v['brand']} não conseguiu entregar seu cartão{_opt(v['card'], ' com final ' + str(v['card']))}." if v["failed"] else f"{v['brand']}: seu cartão{_opt(v['card'], ' com final ' + str(v['card']))} está a caminho.",
    ),
    "debt_offer": _t(
        lambda v: f"{v['brand']} te ofrece liquidar un adeudo{_opt(v['amount'], ' con ' + str(v['amount']))}; verifica con tu banco antes de pagar.",
        lambda v: f"{v['brand']} offers to settle a debt{_opt(v['amount'], ' for ' + str(v['amount']))}; check with your bank before paying.",
        lambda v: f"{v['brand']} propose de solder une dette{_opt(v['amount'], ' pour ' + str(v['amount']))} ; vérifiez auprès de votre banque avant de payer.",
        lambda v: f"{v['brand']} propone di saldare un debito{_opt(v['amount'], ' con ' + str(v['amount']))}; verifica con la tua banca prima di pagare.",
        lambda v: f"{v['brand']} oferece quitar uma dívida{_opt(v['amount'], ' por ' + str(v['amount']))}; confirme com seu banco antes de pagar.",
    ),
    "debt_overdue": _t(
        lambda v: f"{v['brand']}: tienes un pago vencido{_opt(v['amount'], '; te piden ' + str(v['amount']))}{_opt(v['due'], ' (la fecha límite fue el ' + str(v['due']) + ')')}.",
        lambda v: f"{v['brand']}: you have an overdue payment{_opt(v['amount'], '; they ask for ' + str(v['amount']))}{_opt(v['due'], ' (it was due ' + str(v['due']) + ')')}.",
        lambda v: f"{v['brand']} : vous avez un paiement en retard{_opt(v['amount'], ' ; on vous demande ' + str(v['amount']))}{_opt(v['due'], ' (échéance : ' + str(v['due']) + ')')}.",
        lambda v: f"{v['brand']}: hai un pagamento scaduto{_opt(v['amount'], '; ti chiedono ' + str(v['amount']))}{_opt(v['due'], ' (scadenza: ' + str(v['due']) + ')')}.",
        lambda v: f"{v['brand']}: você tem um pagamento vencido{_opt(v['amount'], '; pedem ' + str(v['amount']))}{_opt(v['due'], ' (vencimento: ' + str(v['due']) + ')')}.",
    ),
    "bill_due": _t(
        lambda v: f"{v['brand']}: tienes un pago pendiente{_opt(v['amount'], ' de ' + str(v['amount']))}{_opt(v['due'], ' con fecha límite ' + str(v['due']))}.",
        lambda v: f"{v['brand']}: you have a pending payment{_opt(v['amount'], ' of ' + str(v['amount']))}{_opt(v['due'], ' with due date ' + str(v['due']))}.",
        lambda v: f"{v['brand']} : vous avez un paiement en attente{_opt(v['amount'], ' de ' + str(v['amount']))}{_opt(v['due'], ' avec échéance le ' + str(v['due']))}.",
        lambda v: f"{v['brand']}: hai un pagamento in sospeso{_opt(v['amount'], ' di ' + str(v['amount']))}{_opt(v['due'], ' con scadenza ' + str(v['due']))}.",
        lambda v: f"{v['brand']}: você tem um pagamento pendente{_opt(v['amount'], ' de ' + str(v['amount']))}{_opt(v['due'], ' com vencimento em ' + str(v['due']))}.",
    ),
    "order_delivered": _t(
        lambda v: f"Tu pedido de {v['brand']} ya fue entregado.",
        lambda v: f"Your {v['brand']} order was delivered.",
        lambda v: f"Votre commande {v['brand']} a été livrée.",
        lambda v: f"Il tuo ordine {v['brand']} è stato consegnato.",
        lambda v: f"Seu pedido de {v['brand']} foi entregue.",
    ),
    "order_shipped": _t(
        lambda v: f"Tu pedido de {v['brand']} va en camino{_opt(v['date'], ' (' + str(v['date']) + ')')}.",
        lambda v: f"Your {v['brand']} order is on its way{_opt(v['date'], ' (' + str(v['date']) + ')')}.",
        lambda v: f"Votre commande {v['brand']} est en route{_opt(v['date'], ' (' + str(v['date']) + ')')}.",
        lambda v: f"Il tuo ordine {v['brand']} è in arrivo{_opt(v['date'], ' (' + str(v['date']) + ')')}.",
        lambda v: f"Seu pedido de {v['brand']} está a caminho{_opt(v['date'], ' (' + str(v['date']) + ')')}.",
    ),
    "order_placed": _t(
        lambda v: f"Hiciste una compra en {v['brand']}{_opt(v['amount'], ' por ' + str(v['amount']))}.",
        lambda v: f"You made a purchase at {v['brand']}{_opt(v['amount'], ' for ' + str(v['amount']))}.",
        lambda v: f"Vous avez fait un achat chez {v['brand']}{_opt(v['amount'], ' de ' + str(v['amount']))}.",
        lambda v: f"Hai fatto un acquisto su {v['brand']}{_opt(v['amount'], ' di ' + str(v['amount']))}.",
        lambda v: f"Você fez uma compra em {v['brand']}{_opt(v['amount'], ' de ' + str(v['amount']))}.",
    ),
    "transfer_received": _t(
        lambda v: f"Recibiste {v['amount'] or 'un pago'}{_opt(v['date'], ' el ' + str(v['date']))} ({v['brand']}).",
        lambda v: f"You received {v['amount'] or 'a payment'}{_opt(v['date'], ' on ' + str(v['date']))} ({v['brand']}).",
        lambda v: f"Vous avez reçu {v['amount'] or 'un paiement'}{_opt(v['date'], ' le ' + str(v['date']))} ({v['brand']}).",
        lambda v: f"Hai ricevuto {v['amount'] or 'un pagamento'}{_opt(v['date'], ' il ' + str(v['date']))} ({v['brand']}).",
        lambda v: f"Você recebeu {v['amount'] or 'um pagamento'}{_opt(v['date'], ' em ' + str(v['date']))} ({v['brand']}).",
    ),
    "transfer_sent": _t(
        lambda v: f"Enviaste {v['amount'] or 'una transferencia'}{_opt(v['date'], ' el ' + str(v['date']))} desde {v['brand']}.",
        lambda v: f"You sent {v['amount'] or 'a transfer'}{_opt(v['date'], ' on ' + str(v['date']))} from {v['brand']}.",
        lambda v: f"Vous avez envoyé {v['amount'] or 'un virement'}{_opt(v['date'], ' le ' + str(v['date']))} depuis {v['brand']}.",
        lambda v: f"Hai inviato {v['amount'] or 'un bonifico'}{_opt(v['date'], ' il ' + str(v['date']))} da {v['brand']}.",
        lambda v: f"Você enviou {v['amount'] or 'uma transferência'}{_opt(v['date'], ' em ' + str(v['date']))} pelo {v['brand']}.",
    ),
    "statement": _t(
        lambda v: f"{v['brand']}: tu estado de cuenta ya está disponible.",
        lambda v: f"{v['brand']}: your statement is available.",
        lambda v: f"{v['brand']} : votre relevé est disponible.",
        lambda v: f"{v['brand']}: il tuo estratto conto è disponibile.",
        lambda v: f"{v['brand']}: seu extrato está disponível.",
    ),
    "receipt": _t(
        lambda v: f"{v['brand']} te envió un comprobante o factura{_opt(v['amount'], ' por ' + str(v['amount']))}.",
        lambda v: f"{v['brand']} sent you a receipt or invoice{_opt(v['amount'], ' for ' + str(v['amount']))}.",
        lambda v: f"{v['brand']} vous a envoyé un reçu ou une facture{_opt(v['amount'], ' de ' + str(v['amount']))}.",
        lambda v: f"{v['brand']} ti ha inviato una ricevuta o fattura{_opt(v['amount'], ' di ' + str(v['amount']))}.",
        lambda v: f"{v['brand']} enviou um comprovante ou fatura{_opt(v['amount'], ' de ' + str(v['amount']))}.",
    ),
    "security_alert": _t(
        lambda v: f"{v['brand']}: aviso de seguridad de tu cuenta; revisa si fuiste tú.",
        lambda v: f"{v['brand']}: security notice for your account; check it was you.",
        lambda v: f"{v['brand']} : alerte de sécurité sur votre compte ; vérifiez que c’était vous.",
        lambda v: f"{v['brand']}: avviso di sicurezza sul tuo account; verifica che fossi tu.",
        lambda v: f"{v['brand']}: aviso de segurança da sua conta; confira se foi você.",
    ),
    "verification_code": _t(
        lambda v: f"{v['brand']} te envió un código de acceso; no lo compartas.",
        lambda v: f"{v['brand']} sent you an access code; don’t share it.",
        lambda v: f"{v['brand']} vous a envoyé un code d’accès ; ne le partagez pas.",
        lambda v: f"{v['brand']} ti ha inviato un codice di accesso; non condividerlo.",
        lambda v: f"{v['brand']} enviou um código de acesso; não o compartilhe.",
    ),
    "magic_link": _t(
        lambda v: f"{v['brand']} te envió un enlace para entrar o confirmar tu cuenta.",
        lambda v: f"{v['brand']} sent you a link to sign in or confirm your account.",
        lambda v: f"{v['brand']} vous a envoyé un lien pour vous connecter ou confirmer votre compte.",
        lambda v: f"{v['brand']} ti ha inviato un link per accedere o confermare l’account.",
        lambda v: f"{v['brand']} enviou um link para entrar ou confirmar sua conta.",
    ),
    "terms_update": _t(
        lambda v: f"{v['brand']} actualizó sus condiciones o su aviso de privacidad.",
        lambda v: f"{v['brand']} updated its terms or privacy notice.",
        lambda v: f"{v['brand']} a mis à jour ses conditions ou sa politique de confidentialité.",
        lambda v: f"{v['brand']} ha aggiornato le condizioni o l’informativa sulla privacy.",
        lambda v: f"{v['brand']} atualizou seus termos ou aviso de privacidade.",
    ),
    "job": _t(
        lambda v: f"{v['brand']}: algunas invitaciones a entrevista vencen el {v['due']}." if v["interview"] and v["due"] else f"{v['brand']}: {'tienes invitaciones a entrevista' + (' que vencen pronto' if v['expiring'] else '') if v['interview'] else ('respondió sobre tu postulación' if v['reply'] else 'novedades de empleo')} — «{v['topic']}».",
        lambda v: f"{v['brand']}: some interview invitations expire on {v['due']}." if v["interview"] and v["due"] else f"{v['brand']}: {'you have interview invitations' + (' expiring soon' if v['expiring'] else '') if v['interview'] else ('replied about your application' if v['reply'] else 'job update')} — “{v['topic']}”.",
        lambda v: f"{v['brand']} : certaines invitations à un entretien expirent le {v['due']}." if v["interview"] and v["due"] else f"{v['brand']} : {'vous avez des invitations à un entretien' + (' qui expirent bientôt' if v['expiring'] else '') if v['interview'] else ('a répondu à votre candidature' if v['reply'] else 'nouvelles d’emploi')} — « {v['topic']} ».",
        lambda v: f"{v['brand']}: alcuni inviti a colloqui scadono il {v['due']}." if v["interview"] and v["due"] else f"{v['brand']}: {'hai inviti a colloqui' + (' in scadenza' if v['expiring'] else '') if v['interview'] else ('ha risposto alla tua candidatura' if v['reply'] else 'novità di lavoro')} — «{v['topic']}».",
        lambda v: f"{v['brand']}: alguns convites para entrevista vencem em {v['due']}." if v["interview"] and v["due"] else f"{v['brand']}: {'você tem convites para entrevista' + (' que vencem em breve' if v['expiring'] else '') if v['interview'] else ('respondeu sobre sua candidatura' if v['reply'] else 'novidades de emprego')} — «{v['topic']}».",
    ),
    "gov_procedure": _t(
        lambda v: f"{v['brand']} te escribió sobre un trámite: «{v['topic']}».",
        lambda v: f"{v['brand']} wrote to you about a procedure: “{v['topic']}”.",
        lambda v: f"{v['brand']} vous a écrit au sujet d’une démarche : « {v['topic']} ».",
        lambda v: f"{v['brand']} ti ha scritto per una pratica: «{v['topic']}».",
        lambda v: f"{v['brand']} escreveu sobre um trâmite: «{v['topic']}».",
    ),
    "promo": _t(
        lambda v: f"Publicidad de {v['brand']}: «{v['topic']}».",
        lambda v: f"Advertising from {v['brand']}: “{v['topic']}”.",
        lambda v: f"Publicité de {v['brand']} : « {v['topic']} ».",
        lambda v: f"Pubblicità di {v['brand']}: «{v['topic']}».",
        lambda v: f"Publicidade de {v['brand']}: «{v['topic']}».",
    ),
    "personal": _t(
        lambda v: f"{v['brand']} te escribió: «{v['lead']}».",
        lambda v: f"{v['brand']} wrote to you: “{v['lead']}”.",
        lambda v: f"{v['brand']} vous a écrit : « {v['lead']} ».",
        lambda v: f"{v['brand']} ti ha scritto: «{v['lead']}».",
        lambda v: f"{v['brand']} escreveu: «{v['lead']}».",
    ),
    "unknown": _t(
        lambda v: f"{v['brand']} te escribió sobre «{v['topic']}».",
        lambda v: f"{v['brand']} wrote to you about “{v['topic']}”.",
        lambda v: f"{v['brand']} vous a écrit au sujet de « {v['topic']} ».",
        lambda v: f"{v['brand']} ti ha scritto riguardo a «{v['topic']}».",
        lambda v: f"{v['brand']} escreveu sobre «{v['topic']}».",
    ),
}
_SOMEONE = {"es": "Un remitente", "en": "A sender", "fr": "Un expéditeur", "it": "Un mittente", "pt": "Um remetente"}


def build_main_idea(kind: str, facts: dict[str, Any], subject: str, clean: CleanEmail, direction: str | None = None) -> dict[str, str]:
    head = fold(f"{subject}\n{clean.text[:1500]}")
    lead = _lead_sentence(clean, subject)
    base: Vars = {
        "merchant": facts.get("merchant"),
        "amount": _amt(facts.get("amount")),
        "due": facts.get("due_date"),
        "date": facts.get("due_date") or facts.get("date"),
        "card": facts.get("card_last4"),
        "topic": _topic(subject),
        "lead": lead or _topic(subject),
        "insufficient": "saldo insuficiente" in head or "insufficient funds" in head,
        "failed": bool(re.search(r"no (?:fue posible|pudimos|se pudo) entregar|devuelta", head)),
        "interview": "entrevista" in head or "interview" in head,
        "expiring": bool(re.search(r"venceran|vencen pronto|expir", head)),
        "reply": bool(re.match(r"^(?:re|rv)\s*:", fold(subject))),
    }
    if kind == "transfer_sent":
        base["date"] = facts.get("date")
    templates = TEMPLATES.get(kind) or TEMPLATES["unknown"]
    out: dict[str, str] = {}
    for lang in LANGS:
        values = dict(base, brand=facts.get("brand") or _SOMEONE[lang])
        sentence = templates[lang](values)
        sentence = re.sub(r"\s{2,}", " ", sentence).strip()
        out[lang] = re.sub(r"\.(?:\s*\.)+", ".", sentence)
    return out


# ---------------------------------------------------------------- excerpts

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ¿¡\d\"“«])")
_ACTION = re.compile(
    r"\b(?:paga|pague|liquida|liquide|liquides|realiza tu pago|realice su pago|comun[ií]cate|comun[ií]quese|llama|llame|confirma|confirme|revisa|revise"
    r"|actualiza|actualice|evita|evite|te solicitamos|le solicitamos|requerimos|debes|deber[aá]s|consulta|please|pay|update|call|contact|verify|review)\b",
    re.IGNORECASE,
)
_GREETING = re.compile(
    r"^(?:hola|hi|hello|estimad[oa]s?|buen(?:os|as) (?:d[ií]as|tardes|noches)|querid[oa]|dear|bonjour|ciao|ol[aá])\b[^.!?]{0,60}[,:!]?$",
    re.IGNORECASE,
)
_CONTACT = re.compile(r"^(?:cont[aá]ctanos|l[ií]nea \w+|tel[eé]fono|whatsapp|soporte|ayuda@|www\.)", re.IGNORECASE)
_KIND_WORDS = re.compile(
    r"rechaz|insuficiente|autoriza|vencid|vence|adeudo|pago|cobro|entreg|camino|tarjeta|transfer|spei|importe|monto|estado de cuenta|factura|comprobante"
    r"|seguridad|inicio de sesi|contrase|entrevista|postulaci|declined|due|payment|delivered|shipped|security",
    re.IGNORECASE,
)
_CODE_DIGITS = re.compile(r"\b\d{4,8}\b")
_WORDS = re.compile(r"[^\W\d_]{3,}")


def _candidates(clean: CleanEmail) -> list[tuple[int, int, str]]:
    found: list[tuple[int, int, str]] = []
    order = 0
    for line in clean.lines:
        for piece in _SENTENCE_SPLIT.split(line):
            sentence = piece.strip()
            if sentence:
                found.append((order, len(sentence), sentence))
                order += 1
    return found


def _lead_sentence(clean: CleanEmail, subject: str) -> str | None:
    subject_key = fold(strip_subject_prefix(clean_subject(subject)))
    for _, length, sentence in _candidates(clean):
        if length < 12 or _GREETING.match(sentence) or fold(sentence) == subject_key:
            continue
        return sentence if length <= 120 else sentence[:119].rstrip() + "…"
    return None


def select_excerpts(clean: CleanEmail, subject: str, kind: str, facts: dict[str, Any]) -> list[str]:
    subject_key = fold(strip_subject_prefix(clean_subject(subject)))
    scored: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    for order, length, sentence in _candidates(clean):
        # "$0" (no fee) is not an amount worth quoting.
        has_amount = any(re.search(r"[1-9]", match.group(0)) for match in _AMOUNT.finditer(sentence))
        has_date = bool(_DATE.search(sentence))
        if length < 8 or length > 280:
            continue
        if length < 14 and not (has_amount or has_date):
            continue
        key = fold(sentence)
        if key in seen or key == subject_key or _GREETING.match(sentence) or _CONTACT.match(sentence):
            continue
        # "Asunto: <subject>" / "Subject: <subject>" lines repeat the subject.
        if subject_key and subject_key in key and length <= len(subject_key) + 14:
            continue
        if kind == "verification_code" and _CODE_DIGITS.search(sentence):
            continue
        # A bare date, time or reference number says nothing on its own.
        if len(_WORDS.findall(sentence)) < (1 if has_amount else 2):
            continue
        if re.match(r"^(?:asunto|subject|objet|oggetto|assunto)\s*:", key):
            continue
        seen.add(key)
        score = 0
        score += 3 if has_amount else 0
        score += 2 if has_date else 0
        score += 3 if _DUE_CUE.search(sentence) and has_date else 0
        score += 2 if _ACTION.search(sentence) else 0
        score += 2 if _KIND_WORDS.search(sentence) else 0
        if facts.get("merchant") and facts["merchant"] in sentence:
            score += 3
        if facts.get("reference") and facts["reference"] in sentence:
            score += 1
        if length > 200:
            score -= 1
        if score > 0:
            scored.append((-score, order, sentence))
    limit = 1 if kind in {"promo", "verification_code", "magic_link"} else MAX_EXCERPTS
    best = sorted(scored)[:limit]
    if not best and kind not in {"verification_code"}:
        lead = next(
            (s for _, length, s in _candidates(clean) if 20 <= length <= 280 and fold(s) != subject_key and not _GREETING.match(s)),
            None,
        )
        return verified_excerpts([lead] if lead else [], clean)
    return verified_excerpts([sentence for _, _, sentence in sorted(best, key=lambda item: item[1])], clean)


def verified_excerpts(excerpts: list[str], clean: CleanEmail) -> list[str]:
    """Only quotes that appear verbatim in the cleaned text survive."""
    return [quote for quote in excerpts if quote and quote in clean.text]


# ---------------------------------------------------------------- entry point

def build_insight(message: dict[str, Any]) -> dict[str, Any]:
    subject = clean_subject(message.get("subject"))
    sender = message.get("sender")
    clean = clean_email(message.get("body_text") or message.get("snippet"), message.get("body_html"), subject)
    facts = extract_facts(subject, clean, sender)
    kind = detect_kind(subject, clean, sender, message.get("triage_category"))
    return {
        "version": INSIGHT_VERSION,
        "kind": kind,
        "area": KIND_AREA.get(kind),
        "main_idea": build_main_idea(kind, facts, subject, clean, message.get("direction")),
        "excerpts": select_excerpts(clean, subject, kind, facts),
        "facts": facts,
        "preview": preview_text(clean) or subject,
        "clean_source": clean.source,
        "removed": clean.removed,
    }


def safe_insight(message: dict[str, Any] | None) -> dict[str, Any] | None:
    """``build_insight`` that never breaks an endpoint."""
    if not message:
        return None
    try:
        return build_insight(message)
    except Exception:  # pragma: no cover - defensive: insights are optional
        return None
