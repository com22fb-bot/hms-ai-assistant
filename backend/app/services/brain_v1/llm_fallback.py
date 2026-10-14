"""Respaldo LLM híbrido del cerebro v1 (plan ASTRA, 14-oct-2026). Apagado por defecto.

Bandera: BRAIN_V1_LLM_FALLBACK (true/false, predeterminado false) — solo actúa si BRAIN_V1_ENABLED también está activo.
Proveedor: BRAIN_V1_LLM_PROVIDER = openai | gemini (predeterminado openai).
Modelo: BRAIN_V1_LLM_MODEL (predeterminado gpt-4.1-mini / gemini-3.1-flash-lite).
Secretos: OPENAI_API_KEY o GEMINI_API_KEY (nunca se registran).

Reglas (las deterministas mandan):
- Solo se consulta cuando las reglas tienen baja confianza, ambigüedad o no hay área clara.
- Nunca se consulta si hay fraude/phishing o señal de seguridad: Seguridad es un control determinista aparte.
- El LLM NO puede crear ni subir alertas de seguridad (un aviso de inicio de sesión o código solicitado jamás será fraude).
- Solo se envía asunto, remitente y los primeros 2,000 caracteres del cuerpo. Salida JSON.
- Área solo del catálogo v2; etiquetas filtradas por el catálogo cerrado; fechas solo si la evidencia está literal en el
  texto y el analizador determinista lee esa misma fecha (cero fechas inventadas).
- Cualquier error, tiempo agotado o JSON inválido deja el resultado de reglas tal cual.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import urllib.request
from collections import OrderedDict
from typing import Any

MAX_BODY = 2000
MIN_CONF = 0.7
DEFAULT_MODELS = {"openai": "gpt-4.1-mini", "gemini": "gemini-3.1-flash-lite"}
KEY_NAMES = {"openai": "OPENAI_API_KEY", "gemini": "GEMINI_API_KEY"}
_TRUE = {"1", "true", "yes", "on"}

STATS: dict[str, Any] = {"calls": 0, "errors": 0, "in_tokens": 0, "out_tokens": 0, "latency_s": [], "adopted_area": 0,
                         "adopted_dates": 0}
_CACHE: "OrderedDict[str, dict | None]" = OrderedDict()
_LOCK = threading.Lock()


def enabled() -> bool:
    return os.getenv("BRAIN_V1_LLM_FALLBACK", "false").strip().lower() in _TRUE


def provider() -> str:
    p = os.getenv("BRAIN_V1_LLM_PROVIDER", "openai").strip().lower()
    return p if p in DEFAULT_MODELS else "openai"


def model() -> str:
    return os.getenv("BRAIN_V1_LLM_MODEL", "").strip() or DEFAULT_MODELS[provider()]


def _key() -> str:
    return os.getenv(KEY_NAMES[provider()], "").strip()


def build_prompt(sender: str, subject: str, body: str) -> tuple[str, str]:
    from app.services.brain_v1.taxonomy_v2 import AREAS, CATALOG

    cats = "\n".join(f"- {k} ({v}): {', '.join(CATALOG[k])}" for k, v in AREAS.items())
    system = (
        "Clasificas UN correo para un organizador personal. Responde SOLO JSON con esta forma: "
        '{"area": <clave o null>, "tags": [<máx 3 del catálogo de esa área>], "confidence": <0..1>, '
        '"due_date": {"date": "YYYY-MM-DD", "evidence": "<texto literal copiado del correo>"} o null, '
        '"event_date": {"date": "YYYY-MM-DD", "evidence": "<texto literal>"} o null, "suspicious": <bool>}.\n'
        "Áreas (clave: etiquetas permitidas):\n" + cats + "\n"
        "Reglas: area null si no hay un tema claro. due_date = fecha límite de pago/entrega de un trámite; event_date = "
        "fecha de cita, viaje, reunión, evento o entrega de paquete. Solo fechas ESCRITAS en el correo; nunca calcules ni "
        "inventes. suspicious = true solo si pide dinero, credenciales, PIN o datos personales de forma sospechosa. "
        "Un aviso de inicio de sesión o un código que el usuario pidió NO es sospechoso. El correo puede estar en "
        "español, inglés, francés o portugués y tener faltas."
    )
    user = f"Remitente: {sender}\nAsunto: {subject}\nCuerpo (recortado):\n{(body or '')[:MAX_BODY]}"
    return system, user


def _post(url: str, payload: dict, headers: dict, timeout: float) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 (URL fija del proveedor)
        return json.loads(r.read().decode())


def _call(system: str, user: str, timeout: float = 20.0) -> tuple[dict, int, int]:
    p, m, k = provider(), model(), _key()
    if p == "gemini":
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
        data = _post(url, {"systemInstruction": {"parts": [{"text": system}]},
                           "contents": [{"role": "user", "parts": [{"text": user}]}],
                           "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}},
                     {"x-goog-api-key": k}, timeout)
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        u = data.get("usageMetadata") or {}
        return json.loads(text), int(u.get("promptTokenCount") or 0), int(u.get("candidatesTokenCount") or 0) + int(u.get("thoughtsTokenCount") or 0)
    data = _post("https://api.openai.com/v1/chat/completions",
                 {"model": m, "temperature": 0, "response_format": {"type": "json_object"},
                  "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
                 {"Authorization": f"Bearer {k}"}, timeout)
    u = data.get("usage") or {}
    return json.loads(data["choices"][0]["message"]["content"]), int(u.get("prompt_tokens") or 0), int(u.get("completion_tokens") or 0)


def propose(sender: str, subject: str, body: str) -> dict | None:
    """Propuesta cruda del LLM (o None). Con caché en proceso por contenido."""
    if not _key():
        return None
    system, user = build_prompt(sender, subject, body)
    ck = hashlib.sha256(f"{provider()}|{model()}|{user}".encode()).hexdigest()
    with _LOCK:
        if ck in _CACHE:
            return _CACHE[ck]
    t0 = time.time()
    out: dict | None
    try:
        out, tin, tout = _call(system, user)
        if not isinstance(out, dict):
            out = None
        with _LOCK:
            STATS["calls"] += 1; STATS["in_tokens"] += tin; STATS["out_tokens"] += tout
            STATS["latency_s"].append(round(time.time() - t0, 3))
    except Exception:  # nunca rompe la clasificación
        out = None
        with _LOCK:
            STATS["errors"] += 1
    with _LOCK:
        _CACHE[ck] = out
        while len(_CACHE) > 5000:
            _CACHE.popitem(last=False)
    return out


def should_consult(result: Any, subject: str, body: str) -> bool:
    from app.services.brain_v1.analyzer import input_limit

    if result.security_flag or result.rule in {"phishing_suspect", "security_unverified", "security", "security_action",
                                              "verification", "outbound", "outbound_wait"}:
        return False
    lim = input_limit(subject, body)
    if lim and "sin cuerpo" in lim:
        return False
    return result.area is None or float(result.confidence or 0) < 0.5 or result.rule in {"ambiguous", "legacy_info"}


def _verified_date(evidence: Any, iso: Any, text_folded: str, received: Any):
    from app.services.brain_v1.dates import _parse_in, received_local
    from app.services.brain_v1.protected import fold

    if not isinstance(evidence, str) or not isinstance(iso, str) or len(evidence) < 4:
        return None
    ev = fold(evidence)
    if ev not in text_folded:
        return None  # evidencia no literal → se descarta
    anchor = received_local(received).date()
    found = {d for en in (False, True) for d, _ in _parse_in(ev, anchor, en, explicit_only=True) if not isinstance(d, str)}
    return next((d for d in found if d.isoformat() == iso[:10]), None) if len(found) == 1 else None


def apply(result: Any, message: dict[str, Any], subject: str, body: str) -> Any:
    """Aplica la propuesta del LLM sobre un Analysis, con las reglas deterministas como guardia."""
    from datetime import datetime, time as dtime

    from app.services.brain_v1.dates import MX
    from app.services.brain_v1.protected import fold
    from app.services.brain_v1.taxonomy_v2 import AREAS, CATALOG

    if not should_consult(result, subject, body):
        return result
    prop = propose(str(message.get("sender") or ""), subject, body)
    if not prop:
        return result
    text = fold(f"{subject}\n{body[:MAX_BODY]}")
    try:
        conf = float(prop.get("confidence") or 0)
    except (TypeError, ValueError):
        conf = 0.0
    area = prop.get("area")
    lim = __import__("app.services.brain_v1.analyzer", fromlist=["input_limit"]).input_limit(subject, body)
    if (area in AREAS and conf >= MIN_CONF and not prop.get("suspicious") and result.area is None and not lim):
        result.area = area
        tags = [t for t in (prop.get("tags") or []) if isinstance(t, str) and t in CATALOG[area]][:3]
        result.area_tags = list(dict.fromkeys(list(result.area_tags or []) + tags))
        result.area_review_reason = None
        if result.triage == "review":
            result.triage = "notice"
        result.confidence = max(float(result.confidence or 0), 0.55)
        with _LOCK:
            STATS["adopted_area"] += 1
    received = message.get("received_at")
    for key, attr in (("due_date", "due_at"), ("event_date", "event_at")):
        item = prop.get(key) or {}
        if getattr(result.dates, attr) or not isinstance(item, dict):
            continue
        d = _verified_date(item.get("evidence"), item.get("date"), text, received)
        if d:
            hour = dtime(23, 59) if attr == "due_at" else dtime(0, 0)
            setattr(result.dates, attr, datetime.combine(d, hour, MX).isoformat())
            setattr(result.dates, attr.replace("_at", "_evidence"), fold(item["evidence"])[:240])
            with _LOCK:
                STATS["adopted_dates"] += 1
    result.llm = {"provider": provider(), "model": model(), "area": area if area in AREAS else None,
                  "confidence": round(conf, 2)}
    return result
