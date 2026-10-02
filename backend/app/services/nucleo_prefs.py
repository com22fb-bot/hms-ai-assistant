"""Validación pura de preferencias Núcleo IA. Sin acceso a base de datos."""

from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException


_THEMES = {"nucleo", "nucleo-claro", "command", "day"}
_KINDS = {"sender", "case_type", "subject", "concept"}
_SCALES = (0.9, 1.0, 1.25, 1.5)
_MAX_BYTES = 48_000


def schema_gap(error: BaseException) -> bool:
    text = str(error).lower()
    return any(
        token in text
        for token in (
            "pgrst204",
            "pgrst205",
            "42p01",
            "42703",
            "does not exist",
            "schema cache",
            "could not find",
        )
    )


def sanitize_preferences(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise HTTPException(
            status_code=422,
            detail={
                "status": "invalid_preferences",
                "message": "Las preferencias deben ser un objeto.",
            },
        )
    theme = raw.get("theme") if raw.get("theme") in _THEMES else "nucleo"
    try:
        scale = float(raw.get("fontScale", 1))
    except (TypeError, ValueError):
        scale = 1.0
    font_scale = min(_SCALES, key=lambda item: abs(item - scale))
    try:
        volume = float(raw.get("volume", 0.8))
    except (TypeError, ValueError):
        volume = 0.8
    volume = min(1.0, max(0.0, volume))
    try:
        rate = float(raw.get("speechRate", 1))
    except (TypeError, ValueError):
        rate = 1.0
    rate = min(1.5, max(0.8, rate))

    snooze_in = raw.get("snooze") if isinstance(raw.get("snooze"), dict) else {}
    snooze: dict[str, str] = {}
    for key, value in list(snooze_in.items())[:200]:
        if isinstance(key, str) and isinstance(value, str) and len(key) <= 120:
            snooze[key] = value[:40]

    rules_in = raw.get("alertRules") if isinstance(raw.get("alertRules"), list) else []
    rules: list[dict[str, Any]] = []
    for item in rules_in[:40]:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "")
        value = str(item.get("value") or "").strip()
        rule_id = str(item.get("id") or "").strip()
        if kind not in _KINDS or not value or not rule_id:
            continue
        area = item.get("area")
        rules.append(
            {
                "id": rule_id[:80],
                "kind": kind,
                "value": value[:200],
                "enabled": bool(item.get("enabled", True)),
                "area": area if isinstance(area, str) and len(area) <= 40 else None,
            }
        )

    completed = raw.get("pushOnboardingCompletedAt")
    top10 = raw.get("top10SeenAt")
    clean = {
        "theme": theme,
        "fontScale": font_scale,
        "highContrast": bool(raw.get("highContrast")),
        "reducedMotion": bool(raw.get("reducedMotion")),
        "screenReader": bool(raw.get("screenReader", True)),
        "readAloud": bool(raw.get("readAloud", True)),
        "speechRate": rate,
        "visualAlerts": bool(raw.get("visualAlerts", True)),
        "badges": bool(raw.get("badges", True)),
        "flash": bool(raw.get("flash", True)),
        "vibrate": bool(raw.get("vibrate", True)),
        "captions": bool(raw.get("captions", True)),
        "transcript": bool(raw.get("transcript", True)),
        "guide": bool(raw.get("guide", True)),
        "soundEnabled": bool(raw.get("soundEnabled", True)),
        "volume": volume,
        "snooze": snooze,
        "pushOnboardingCompletedAt": completed if isinstance(completed, str) else None,
        "top10SeenAt": top10[:40] if isinstance(top10, str) else None,
        "alertRules": rules,
    }
    if len(json.dumps(clean)) > _MAX_BYTES:
        raise HTTPException(
            status_code=422,
            detail={
                "status": "preferences_too_large",
                "message": "Las preferencias superan el tamaño permitido.",
            },
        )
    return clean


