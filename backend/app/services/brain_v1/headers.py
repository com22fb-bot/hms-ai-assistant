"""Cabeceras de lista y etiquetas del proveedor (adenda 1.3, punto 5).

Solo con BRAIN_V1_ENABLED: se guarda en communication_messages.mail_headers (jsonb,
migración 20261013_006). Con la bandera apagada no se agrega la llave al insert.
Forma: {"list_unsubscribe": str|None, "list_unsubscribe_post": str|None,
        "list_id": str|None, "provider_labels": [str], "source": "gmail"|"graph"|"imap"}
"""
from __future__ import annotations

from typing import Any, Iterable

_MAX = 1000
WANTED = {"list-unsubscribe": "list_unsubscribe",
          "list-unsubscribe-post": "list_unsubscribe_post",
          "list-id": "list_id"}


def _clean(value: Any) -> str | None:
    text = " ".join(str(value or "").split())
    return text[:_MAX] or None


def _from_pairs(pairs: Iterable[tuple[Any, Any]]) -> dict[str, str | None]:
    out: dict[str, str | None] = {v: None for v in WANTED.values()}
    for name, value in pairs:
        key = WANTED.get(str(name or "").strip().lower())
        if key and out[key] is None:
            out[key] = _clean(value)
    return out


def _labels(values: Iterable[Any] | None) -> list[str]:
    return [str(v)[:200] for v in dict.fromkeys(values or []) if str(v or "").strip()][:50]


def gmail_mail_headers(headers: list[dict[str, Any]] | None, label_ids: Iterable[Any] | None) -> dict[str, Any]:
    pairs = ((h.get("name"), h.get("value")) for h in (headers or []) if isinstance(h, dict))
    return {**_from_pairs(pairs), "provider_labels": _labels(label_ids), "source": "gmail"}


def graph_mail_headers(payload: dict[str, Any]) -> dict[str, Any]:
    raw = payload.get("internetMessageHeaders") or []
    pairs = ((h.get("name"), h.get("value")) for h in raw if isinstance(h, dict))
    labels: list[Any] = list(payload.get("categories") or [])
    inference = payload.get("inferenceClassification")
    if inference:
        labels.append(f"inference:{inference}")
    return {**_from_pairs(pairs), "provider_labels": _labels(labels), "source": "graph"}


def imap_mail_headers(parsed: Any, folder: str | None, flags: Iterable[Any] | None = None) -> dict[str, Any]:
    pairs = list(parsed.items()) if parsed is not None and hasattr(parsed, "items") else []
    labels = ([f"folder:{folder}"] if folder else []) + list(flags or [])
    return {**_from_pairs(pairs), "provider_labels": _labels(labels), "source": "imap"}
