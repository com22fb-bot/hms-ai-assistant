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
