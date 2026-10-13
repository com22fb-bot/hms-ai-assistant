"""C4 · Clave de documento (folio/factura/pedido) e importe.

La clave se extrae con validación: debe tener al menos un dígito, no ser una
fecha, un año suelto, un importe ni un teléfono de 10 dígitos. Se antepone la
marca del remitente para que dos comercios distintos con el mismo folio nunca
se mezclen; la búsqueda del caso es por workspace (todos los buzones).
"""
from __future__ import annotations

import re

from app.services.brain_v1.protected import fold

_LABELS = (
    r"factura|folio fiscal|folio|invoice|pedido|orden de compra|orden|order|recibo|referencia de pago|referencia|"
    r"ref\.?|ticket|no\.? de (?:pedido|orden|factura|cliente|servicio)|numero de (?:pedido|orden|factura|recibo|referencia)"
)
DOC_RE = re.compile(
    r"\b(?:" + _LABELS + r")\s*(?:no\.?|num(?:ero)?\.?|n[°º]|#|:)?\s*#?\s*:?\s*([a-z0-9][a-z0-9\-/]{2,36})",
)
# Variantes: "factura folio XX-0919", "Folio de la factura pagada: AG-1"
DIGIT_DOC_RE = re.compile(r"\b(?:folio|factura|invoice|pedido|orden|order|recibo)\s*(?:no\.?|#|:)?\s*#?\s*([a-z]{0,5}-?\d[a-z0-9\-/]{1,30})")
LABEL_COLON_RE = re.compile(r"\b(?:folio|factura|invoice|pedido|referencia)\b[^:\n]{0,30}:\s*([a-z0-9][a-z0-9\-/]{2,36})")
# A4 (Etapa 1.2): "Factura Telmex No. TX-88213", "Invoice ACME # 991": etiqueta + hasta 2 palabras + No./Núm./#.
LABEL_NUM_RE = re.compile(
    r"\b(?:factura|folio|invoice|pedido|orden|order|recibo)\b(?:\s+[a-z]+){0,2}?\s+(?:no\.?|num(?:ero)?\.?|n[°º]|#)\s*:?\s*([a-z0-9][a-z0-9\-/]{2,36})"
)
HASH_RE = re.compile(r"#\s?([a-z]{0,4}-?\d[a-z0-9\-]{1,20})")
UUID_RE = re.compile(r"\b([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\b")
AMOUNT_RE = re.compile(
    r"(?:\$|mxn|usd|us\$)\s?(\d{1,3}(?:[,]\d{3})+(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)|"
    r"(\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?|\d+\.\d{2})\s?(?:mxn|pesos|usd)"
)
_STOP = {"de", "del", "la", "el", "por", "para", "pago", "fiscal", "electronica", "cfdi", "su", "tu", "your"}


def _valid(token: str) -> bool:
    token = token.strip("-/").lower()
    if len(token) < 3 or token in _STOP or not re.search(r"\d", token):
        return False
    if re.fullmatch(r"(19|20)\d{2}", token):
        return False
    if re.fullmatch(r"\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?", token) or re.fullmatch(r"20\d{2}-\d{1,2}-\d{1,2}", token):
        return False
    if re.fullmatch(r"\d{10}", token):  # teléfono / número de servicio, no folio
        return False
    if re.fullmatch(r"\d{1,3}(,\d{3})*(\.\d{2})?", token):
        return False
    return True


def extract_doc_token(subject: str | None, body: str | None) -> str | None:
    text = fold(f"{subject or ''}\n{(body or '')[:3000]}")
    m = UUID_RE.search(text)
    if m:
        return m[1].upper()
    for pattern in (DOC_RE, DIGIT_DOC_RE, LABEL_NUM_RE, LABEL_COLON_RE, HASH_RE):
        for m in pattern.finditer(text):
            token = m[1].strip("-/.")
            if _valid(token):
                return token.upper()
    return None


def doc_key(brand: str, subject: str | None, body: str | None) -> str | None:
    token = extract_doc_token(subject, body)
    if not token:
        return None
    return f"{brand or 'sin-marca'}:{token}"


def extract_amount(subject: str | None, body: str | None) -> float | None:
    text = fold(f"{subject or ''}\n{(body or '')[:3000]}")
    m = AMOUNT_RE.search(text)
    if not m:
        return None
    raw = (m[1] or m[2] or "").replace(",", "")
    try:
        return round(float(raw), 2)
    except ValueError:
        return None


def amounts_compatible(a: float | None, b: float | None) -> bool:
    if a is None or b is None:
        return False
    return abs(a - b) <= max(1.0, 0.005 * max(a, b))


# --- C4b: sin folio, la clave del caso incluye el periodo -------------------
_MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}
_MONTH_ALT = "|".join(sorted(_MONTHS, key=len, reverse=True))
BILLING_MONTH_RE = re.compile(
    r"\b(?:recibo|factura|estado de cuenta|statement|invoice|bill|mensualidad|cuota|colegiatura|renta|periodo|"
    r"correspondiente a|mes de|consumo de|for)\b[^.\n]{0,25}?\b(" + _MONTH_ALT + r")\b(?:\s+(?:de\s+|del\s+)?(20\d{2}))?"
)
PERIOD_ISO_RE = re.compile(r"\bperiodo:?\s*(20\d{2})-(\d{2})\b")


def billing_period(subject: str | None, body: str | None, received_at) -> tuple[str, str]:
    """('AAAA-MM', 'facturacion'|'recepcion'). Mes de facturación si aparece; si no, mes de recepción (CDMX)."""
    from app.services.brain_v1.dates import received_local

    local = received_local(received_at)
    text = fold(f"{subject or ''}\n{(body or '')[:2000]}")
    m = PERIOD_ISO_RE.search(text)
    if m and 1 <= int(m[2]) <= 12:
        return f"{m[1]}-{m[2]}", "facturacion"
    m = BILLING_MONTH_RE.search(text)
    if m:
        month = _MONTHS[m[1]]
        if m[2]:
            year = int(m[2])
        elif month - local.month > 6:
            year = local.year - 1
        elif local.month - month > 6:
            year = local.year + 1
        else:
            year = local.year
        return f"{year}-{month:02d}", "facturacion"
    return local.strftime("%Y-%m"), "recepcion"


def period_key(brand: str, subject: str | None, body: str | None, received_at) -> str:
    period, _ = billing_period(subject, body, received_at)
    return f"{brand or 'sin-marca'}:periodo:{period}"


_GENERIC_BRAND_TOKENS = {"pagos", "pago", "recibos", "recibo", "facturas", "factura", "facturacion", "cobros", "cobranza",
                         "avisos", "servicios", "clientes", "mail", "info", "notificaciones", "admin", "billing"}


def brand_mentioned(brand: str | None, text: str | None) -> bool:
    """C5b: ¿el texto (p. ej. de un banco) menciona la marca del caso? Ignora palabras genéricas."""
    folded = fold(text or "")
    compact = re.sub(r"[^a-z0-9]", "", folded)
    tokens = [t for t in re.split(r"[-_.]", (brand or "").lower()) if len(t) >= 3 and t not in _GENERIC_BRAND_TOKENS]
    for token in tokens:
        if re.search(r"\b" + re.escape(token) + r"\b", folded) or (len(token) >= 6 and token in compact):
            return True
    return False
