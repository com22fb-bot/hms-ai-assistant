"""Regla única de dirección de un mensaje a partir de sus etiquetas.

Usada por gmail_full_sync (al guardar), case_engine y safe_case_classifier.

- DRAFT manda sobre todo: borrador.
- SENT: saliente, aunque también lleve INBOX (correo que el usuario se envía a
  sí mismo). Quien necesite distinguir ese caso usa ``is_self_delivered``.
- INBOX: entrante.
- Sin etiquetas reconocibles: ``fallback`` (la dirección ya guardada o
  "inbound").
"""
from __future__ import annotations

from collections.abc import Iterable


def _normalize(labels: Iterable[object] | None) -> set[str]:
    return {str(label).upper() for label in (labels or [])}


def direction_from_labels(labels: Iterable[object] | None, fallback: str | None = None) -> str:
    normalized = _normalize(labels)
    if "DRAFT" in normalized:
        return "draft"
    if "SENT" in normalized:
        return "outbound"
    if "INBOX" in normalized:
        return "inbound"
    return str(fallback or "inbound")


def is_self_delivered(labels: Iterable[object] | None) -> bool:
    normalized = _normalize(labels)
    return "SENT" in normalized and "INBOX" in normalized


# ---------------------------------------------------------------------------
# Identidad propia a nivel usuario (auditoría fase 1, H4, issue #195).
# Las direcciones propias son los correos de los buzones conectados del mismo
# workspace. No se infieren alias. La equivalencia de puntos y "+etiqueta"
# solo se aplica a gmail.com/googlemail.com (documentada por Google); en otros
# proveedores la dirección se compara literal (minúsculas, sin espacios).
# ---------------------------------------------------------------------------
from email.utils import getaddresses as _getaddresses

_GMAIL_DOMAINS = {"gmail.com", "googlemail.com"}


def normalize_address(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    parsed = _getaddresses([raw])
    address = (parsed[0][1] if parsed and parsed[0][1] else raw).strip().strip("<>").lower()
    if "@" not in address:
        return ""
    local, domain = address.rsplit("@", 1)
    if domain in _GMAIL_DOMAINS:
        local = local.split("+", 1)[0].replace(".", "")
        domain = "gmail.com"
    return f"{local}@{domain}"


def own_address_set(values: Iterable[object] | None) -> set[str]:
    return {a for a in (normalize_address(v) for v in (values or [])) if a}
