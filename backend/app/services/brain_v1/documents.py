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
    for pattern in (DOC_RE, HASH_RE):
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
