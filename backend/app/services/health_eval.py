"""Evaluación única de salud de Donexto (base del semáforo de /admin y del futuro Centro de control).

Una sola función, `evaluate()`, produce el estado global y el detalle por componente. Las tarjetas y
el semáforo leen ESTA evaluación; nadie calcula colores por su cuenta.

Estados por chequeo:  ok | degradado | falla | sin_verificar
Categoría (por qué):  ok | falla_propia | proveedor_caido | permiso | monitoreo | vencido | timeout | sin_datos
Global:               ROJO  si hay una falla_propia en un componente crítico.
                      AMARILLO si no hay ROJO pero algo está degradado o sin verificar (incluye permisos,
                               proveedor externo caído, monitoreo inaccesible, datos vencidos).
                      VERDE solo si TODOS los chequeos críticos están 'ok' y frescos.
                      (VERIFICANDO es el estado de la interfaz mientras llega la primera evaluación.)

Umbrales (justificación en docs/ops/SEMAFORO_ADMIN.md):
- Base de datos: consulta mínima > 1500 ms = degradado (p95 normal ~150–400 ms desde Railway).
- Cuota de base (Supabase Free 500 MB): >= 80 % degradado, >= 95 % falla (escrituras en riesgo).
- Respaldo diario: <= 30 h ok (cron diario + 6 h de margen), > 30 h degradado, > 54 h o último fallido = falla.
- Errores 5xx en los últimos 15 min (>= 20 peticiones): > 2 % degradado, > 10 % falla.
- Memoria de Railway: >= 90 % del límite degradado.
- Un chequeo que no responde en su tiempo límite queda 'sin_verificar' (timeout), nunca 'ok'.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import httpx

logger = logging.getLogger(__name__)

CACHE_SECONDS = 30
CHECK_TIMEOUT_S = 9
RECOVERY_OK_STREAK = 3          # incidente resuelto tras 3 evaluaciones OK seguidas...
RECOVERY_MIN_SECONDS = 120      # ...que además abarquen al menos 2 minutos.
BACKUP_OK_H, BACKUP_FAIL_H = 30, 54
DB_SLOW_MS = 1500
QUOTA_WARN, QUOTA_FAIL = 80.0, 95.0
ERR_WARN, ERR_FAIL, ERR_MIN_SAMPLE = 2.0, 10.0, 20
MEM_WARN = 90.0
FREE_DB_LIMIT_BYTES = 500 * 1024 * 1024
UA = "Mozilla/5.0 DonextoAdminHealth"

_cache: dict[str, Any] = {}
_lock = threading.Lock()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def result(cid: str, label: str, critical: bool, status: str, kind: str, evidence: str, *,
           data_at: str | None = None, source: str = "", period: str = "", threshold: str = "",
           action: str = "", impact: str = "", hypothesis: str = "", owner: str = "Grok", link: str = "",
           metrics: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"id": cid, "label": label, "critical": critical, "status": status, "kind": kind,
            "evidence": evidence[:300], "checked_at": _now().isoformat(), "data_at": data_at,
            "source": source, "period": period, "threshold": threshold, "action": action,
            "impact": impact, "hypothesis": hypothesis, "owner": owner, "link": link,
            "metrics": metrics or {}}


# --- clasificación de errores de proveedores ----------------------------------------------------

def classify_provider_error(message: str = "", http_status: int | None = None, exc: BaseException | None = None) -> str:
    """permiso (token ausente/inválido/insuficiente) | timeout | proveedor_caido (5xx/red) | monitoreo."""
    text = (message or "").lower()
    if exc is not None:
        if isinstance(exc, (httpx.TimeoutException, FutureTimeout, TimeoutError)):
            return "timeout"
        if isinstance(exc, (httpx.ConnectError, httpx.NetworkError)):
            return "proveedor_caido"
        return "monitoreo"
    if http_status in (401, 403) or any(k in text for k in ("not authorized", "unauthorized", "forbidden",
                                                           "authentication", "invalid token", "permission")):
        return "permiso"
    if http_status is not None and http_status >= 500:
        return "proveedor_caido"
    if http_status == 429:
        return "monitoreo"
    return "monitoreo"


_KIND_TEXT = {
    "permiso": ("El token de monitoreo no tiene permiso (ausente, inválido o insuficiente). "
                "No indica que el proveedor esté caído.", "Revisar o renovar el token de solo lectura."),
    "proveedor_caido": ("El proveedor no responde o devuelve 5xx.", "Revisar la página de estado del proveedor."),
    "timeout": ("La consulta no respondió a tiempo; no se puede afirmar que esté sano ni caído.",
                "Reintentar; si persiste, revisar conectividad del backend."),
    "monitoreo": ("La herramienta de métricas falló; el servicio puede estar sano.", "Revisar la integración de métricas."),
}


# --- chequeos -------------------------------------------------------------------------------------

def check_database(client: Any) -> dict[str, Any]:
    t0 = time.perf_counter()
    try:
        client.table("profiles").select("id").limit(1).execute()
    except Exception as error:  # noqa: BLE001
        return result("database", "Base de datos (Supabase)", True, "falla", "falla_propia",
                      f"Consulta de solo lectura falló: {type(error).__name__}", source="Supabase REST",
                      impact="Sin base no hay inicio de sesión, buzones ni casos.",
                      action="Revisar estado del proyecto en Supabase y SUPABASE_SECRET_KEY.",
                      link="https://supabase.com/dashboard/project/_/logs")
    ms = round((time.perf_counter() - t0) * 1000)
    status = "degradado" if ms > DB_SLOW_MS else "ok"
    return result("database", "Base de datos (Supabase)", True, status, "ok" if status == "ok" else "falla_propia",
                  f"select 1 fila de profiles en {ms} ms", data_at=_now().isoformat(), source="Supabase REST",
                  threshold=f"> {DB_SLOW_MS} ms = degradado", metrics={"latency_ms": ms},
                  action="" if status == "ok" else "Revisar carga o región de Supabase.")


def check_db_quota(client: Any) -> dict[str, Any]:
    try:
        response = client.rpc("admin_db_stats", {}).execute()
        data = response.data if isinstance(response.data, dict) else {}
        if isinstance(response.data, list) and response.data:
            first = response.data[0]
            data = first.get("admin_db_stats", first) if isinstance(first, dict) else {}
        size = data.get("db_size_bytes")
    except Exception as error:  # noqa: BLE001
        return result("db_quota", "Espacio de base", False, "sin_verificar", "monitoreo",
                      f"admin_db_stats falló: {type(error).__name__}", source="RPC admin_db_stats")
    if size is None:
        return result("db_quota", "Espacio de base", False, "sin_verificar", "sin_datos", "La RPC no devolvió tamaño",
                      source="RPC admin_db_stats")
    pct = round(int(size) / FREE_DB_LIMIT_BYTES * 100, 1)
    status = "falla" if pct >= QUOTA_FAIL else "degradado" if pct >= QUOTA_WARN else "ok"
    return result("db_quota", "Espacio de base", status == "falla", status,
                  "ok" if status == "ok" else "falla_propia",
                  f"{round(int(size) / 1048576)} MB de 500 MB (plan Free) = {pct} %", data_at=_now().isoformat(),
                  source="pg_database_size vía admin_db_stats; plan verificado: Supabase Free",
                  threshold=f">= {QUOTA_WARN} % degradado, >= {QUOTA_FAIL} % falla", metrics={"used_pct": pct},
                  action="" if status == "ok" else "Depurar datos o pasar a plan Pro antes de llegar al límite.")


def check_config() -> dict[str, Any]:
    problems = []
    if not os.getenv("ADMIN_EMAILS", "").strip():
        problems.append("ADMIN_EMAILS vacío")
    for var in ("SUPABASE_URL", "SUPABASE_SECRET_KEY"):
        if not os.getenv(var, "").strip():
            problems.append(f"{var} ausente")
    try:
        from app.services import oauth_storage as o
        o._get_encryption_secret()
        o._parse_keyring()
        o._active_key_id()
    except Exception as error:  # noqa: BLE001
        problems.append(f"llavero OAuth inválido ({type(error).__name__})")
    if len(os.getenv("ASSIST_TOKEN_SECRET", "").strip()) < 32:
        problems.append("ASSIST_TOKEN_SECRET ausente o corto")
    for flag in ("BRAIN_V1_ENABLED", "ACCOUNT_CLEANUP_DELETE_ENABLED"):
        if os.getenv(flag, "").strip().lower() in ("1", "true", "yes", "on"):
            problems.append(f"{flag} encendido (debe estar apagado)")
    if problems:
        return result("config", "Autenticación y configuración crítica", True, "falla", "falla_propia",
                      "; ".join(problems), source="variables del proceso (sin valores)",
                      impact="Inicio de sesión, cifrado de credenciales o /asistencia en riesgo.",
                      action="Corregir las variables en Railway (vía Doppler) y redesplegar.")
    return result("config", "Autenticación y configuración crítica", True, "ok", "ok",
                  "Allowlist admin, Supabase, llavero OAuth, secreto de /asistencia y banderas verificados",
                  data_at=_now().isoformat(), source="variables del proceso (sin valores)")


def _http(url: str) -> tuple[int | None, float | None, dict[str, str], BaseException | None]:
    t0 = time.perf_counter()
    try:
        r = httpx.get(url, timeout=8, follow_redirects=False, headers={"user-agent": UA})
        return r.status_code, round((time.perf_counter() - t0) * 1000), dict(r.headers), None
    except Exception as error:  # noqa: BLE001
        return None, None, {}, error


def check_site(cid: str, label: str, url: str, critical: bool, getter: Callable = _http) -> dict[str, Any]:
    status, ms, headers, error = getter(url)
    if error is not None:
        kind = classify_provider_error(exc=error)
        return result(cid, label, critical, "sin_verificar", kind, f"{type(error).__name__} al pedir {url}",
                      source="HTTP desde el backend", link=url, action=_KIND_TEXT.get(kind, ("", ""))[1])
    if status == 403 and str(headers.get("cf-mitigated", "")).lower() == "challenge":
        return result(cid, label, critical, "sin_verificar", "monitoreo",
                      f"HTTP 403 desafío de Cloudflare al monitor ({url})", source="HTTP desde el backend",
                      hypothesis="Bot Fight Mode desafía al monitor; no es una caída.", link=url)
    if status is not None and 200 <= status < 400:
        return result(cid, label, critical, "ok", "ok", f"HTTP {status} en {ms} ms", data_at=_now().isoformat(),
                      source="HTTP desde el backend", metrics={"status": status, "ms": ms}, link=url)
    kind = "proveedor_caido" if status in (520, 521, 522, 523, 524, 525, 526) else "falla_propia"
    return result(cid, label, critical, "falla", kind, f"HTTP {status} en {url}", source="HTTP desde el backend",
                  impact="Los usuarios no pueden abrir esta parte de Donexto.",
                  action="Revisar el último deploy del frontend (Cloudflare Workers) y logs.", link=url)


def check_errors(snapshot: dict[str, Any]) -> dict[str, Any]:
    recent = snapshot.get("recent_15m") or {}
    n, errors = int(recent.get("requests") or 0), int(recent.get("errors_5xx") or 0)
    if n < ERR_MIN_SAMPLE:
        return result("errors", "Errores recientes del backend", False, "sin_verificar", "sin_datos",
                      f"Solo {n} peticiones en 15 min (mínimo {ERR_MIN_SAMPLE} para medir)",
                      source="anillo en memoria del proceso (se reinicia con cada deploy)", period="últimos 15 min")
    pct = round(errors / n * 100, 2)
    status = "falla" if pct > ERR_FAIL else "degradado" if pct > ERR_WARN else "ok"
    return result("errors", "Errores recientes del backend", status == "falla", status,
                  "ok" if status == "ok" else "falla_propia", f"{errors} de {n} peticiones con 5xx ({pct} %)",
                  data_at=_now().isoformat(), source="anillo en memoria del proceso", period="últimos 15 min",
                  threshold=f"> {ERR_WARN} % degradado, > {ERR_FAIL} % falla", metrics={"error_pct": pct, "requests": n})


def check_backup(client: Any, now: datetime | None = None) -> dict[str, Any]:
    now = now or _now()
    try:
        rows = (client.table("admin_events").select("occurred_at,title,status,meta,severity")
                .eq("source", "backup").order("occurred_at", desc=True).limit(20).execute()).data or []
    except Exception as error:  # noqa: BLE001
        return result("backup", "Respaldo diario", True, "sin_verificar", "monitoreo",
                      f"No se pudo leer la Bitácora: {type(error).__name__}", source="Bitácora (admin_events)")
    daily = [r for r in rows if (r.get("meta") or {}).get("kind") == "diario"]
    if not daily:
        return result("backup", "Respaldo diario", True, "sin_verificar", "sin_datos",
                      "No hay eventos de respaldo diario en la Bitácora", source="Bitácora (admin_events)")
    last = daily[0]
    meta = last.get("meta") or {}
    ok_rows = [r for r in daily if (r.get("meta") or {}).get("result") == "ok" and (r.get("meta") or {}).get("verified")]
    last_ok = ok_rows[0] if ok_rows else None
    age_h = None
    if last_ok:
        age_h = round((now - datetime.fromisoformat(str(last_ok["occurred_at"]).replace("Z", "+00:00"))).total_seconds() / 3600, 1)
    failed_last = meta.get("result") not in (None, "ok")
    if last_ok is None or (age_h is not None and age_h > BACKUP_FAIL_H) or failed_last:
        why = ("el último respaldo FALLÓ" if failed_last else
               "no hay respaldo verificado" if last_ok is None else f"último verificado hace {age_h} h")
        return result("backup", "Respaldo diario", True, "falla", "falla_propia", why,
                      data_at=(last_ok or last).get("occurred_at"), source="Bitácora (admin_events, escrita por el workflow tras verificar sha256 en R2)",
                      threshold=f"<= {BACKUP_OK_H} h ok, > {BACKUP_FAIL_H} h o fallido = falla",
                      impact="Si se pierde la base, se perderían los datos desde el último respaldo válido.",
                      action="Revisar Actions «Donexto backup daily» y el Worker donexto-backup-cron.",
                      link="https://github.com/com22fb-bot/hms-ai-assistant/actions/workflows/backup-daily.yml",
                      metrics={"age_h": age_h})
    status = "degradado" if age_h > BACKUP_OK_H else "ok"
    return result("backup", "Respaldo diario", True, status, "ok" if status == "ok" else "vencido",
                  f"Último respaldo verificado hace {age_h} h (sha256 verificado en R2 por el workflow)",
                  data_at=last_ok.get("occurred_at"), source="Bitácora (admin_events)", period="último diario",
                  threshold=f"<= {BACKUP_OK_H} h ok", metrics={"age_h": age_h},
                  action="" if status == "ok" else "Verificar que el cron de las 3:00 am CDMX corrió.")


def check_railway(fetch: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    data = fetch()
    if not data.get("available"):
        kind = data.get("kind") or ("permiso" if data.get("status") == "falta_token" else
                                    classify_provider_error(str(data.get("message", ""))))
        why, action = _KIND_TEXT.get(kind, ("", ""))
        return result("railway", "Railway (métricas y despliegue)", False, "sin_verificar", kind,
                      f"{data.get('message') or data.get('status')}", source="Railway GraphQL",
                      hypothesis=why, action=action,
                      impact="No se ven CPU/memoria ni el último deploy; el backend se verifica aparte (API y base).",
                      link="https://railway.com/project/3721a3d4-c7ce-4399-a716-058ba8afadd4")
    mem, lim = data.get("memory_gb"), data.get("memory_limit_gb")
    pct = round(mem / lim * 100, 1) if mem is not None and lim else None
    deploy = data.get("last_deploy") or {}
    status = "degradado" if pct is not None and pct >= MEM_WARN else "ok"
    if deploy.get("status") and deploy.get("status") not in ("SUCCESS", "SLEEPING"):
        status = "degradado"
    return result("railway", "Railway (métricas y despliegue)", False, status, "ok" if status == "ok" else "falla_propia",
                  f"Último deploy {deploy.get('status')} {deploy.get('commit', '')[:7]}; memoria {pct if pct is not None else 'sin datos'} %",
                  data_at=data.get("metrics_at"), source="Railway GraphQL", period="últimas 24 h, muestras de 15 min",
                  threshold=f"memoria >= {MEM_WARN} % degradado", metrics={"memory_pct": pct, "deploy": deploy})


def check_cloudflare(fetch: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    data = fetch()
    if not data.get("available"):
        kind = "permiso" if data.get("status") == "falta_token" else classify_provider_error(str(data.get("message", "")))
        return result("cloudflare", "Cloudflare (analítica)", False, "sin_verificar", kind,
                      str(data.get("message") or data.get("status")), source="Cloudflare GraphQL",
                      hypothesis=_KIND_TEXT.get(kind, ("", ""))[0])
    return result("cloudflare", "Cloudflare (analítica)", False, "ok", "ok",
                  f"{data.get('requests_7d')} peticiones en 7 días", data_at=_now().isoformat(),
                  source="Cloudflare GraphQL httpRequests1dGroups", period="7 días (UTC, por día)")


# --- global ---------------------------------------------------------------------------------------

def overall(checks: list[dict[str, Any]]) -> dict[str, Any]:
    red = [c for c in checks if c["critical"] and c["status"] == "falla" and c["kind"] in ("falla_propia", "vencido")]
    if red:
        return {"state": "ROJO", "reason": "; ".join(f"{c['label']}: {c['evidence']}" for c in red)}
    yellow = [c for c in checks if c["status"] != "ok"]
    if yellow:
        return {"state": "AMARILLO", "reason": "; ".join(f"{c['label']}: {c['evidence']}" for c in yellow)}
    return {"state": "VERDE", "reason": "Todos los chequeos verificados y actuales."}


def run_checks(checks: dict[str, Callable[[], dict[str, Any]]], meta: dict[str, tuple[str, bool]],
               timeout: float = CHECK_TIMEOUT_S) -> list[dict[str, Any]]:
    out = []
    with ThreadPoolExecutor(max_workers=len(checks)) as pool:
        futures = {cid: pool.submit(fn) for cid, fn in checks.items()}
        deadline = time.monotonic() + timeout
        for cid, fut in futures.items():
            label, critical = meta[cid]
            try:
                out.append(fut.result(timeout=max(0.1, deadline - time.monotonic())))
            except FutureTimeout:
                out.append(result(cid, label, critical, "sin_verificar", "timeout",
                                  f"Sin respuesta en {timeout} s", hypothesis=_KIND_TEXT["timeout"][0]))
            except Exception as error:  # noqa: BLE001
                out.append(result(cid, label, critical, "sin_verificar", "monitoreo",
                                  f"El chequeo falló: {type(error).__name__}"))
    return out


# --- incidentes (Bitácora, deduplicados, con política de recuperación) ---------------------------

def reconcile_incidents(client: Any, checks: list[dict[str, Any]], now: datetime | None = None) -> list[dict[str, Any]]:
    now = now or _now()
    iso = now.isoformat()
    try:
        open_rows = (client.table("admin_events").select("*").eq("source", "monitor").eq("status", "abierto")
                     .order("occurred_at", desc=True).limit(50).execute()).data or []
    except Exception:  # noqa: BLE001
        logger.info("health: no se pudieron leer incidentes", exc_info=True)
        return []
    by_comp = {}
    for row in open_rows:
        comp = (row.get("meta") or {}).get("component")
        if comp and comp not in by_comp:
            by_comp[comp] = row
    for c in checks:
        row = by_comp.get(c["id"])
        bad = c["status"] != "ok" and not (c["kind"] == "sin_datos" and not c["critical"])
        if bad and row is None:
            sev = "critico" if c["critical"] and c["status"] == "falla" else "aviso"
            meta = {"component": c["id"], "kind": c["kind"], "check_status": c["status"], "evidence": c["evidence"],
                    "hypothesis": c["hypothesis"], "impact": c["impact"], "action": c["action"], "owner": c["owner"],
                    "link": c["link"], "last_ok_at": None, "ok_streak": 0, "first_ok_at": None, "last_seen_at": iso,
                    "transitions": [{"at": iso, "to": c["status"]}]}
            try:
                ins = client.table("admin_events").insert({
                    "occurred_at": iso, "source": "monitor", "severity": sev, "status": "abierto",
                    "title": f"{c['label']}: {c['status'].replace('_', ' ')}"[:200], "detail": c["evidence"][:500],
                    "created_by": "semaforo", "meta": meta, "external_id": f"health:{c['id']}:{iso}"}).execute()
                if ins.data:
                    by_comp[c["id"]] = ins.data[0]
            except Exception:  # noqa: BLE001
                logger.info("health: no se pudo abrir incidente", exc_info=True)
        elif row is not None:
            meta = dict(row.get("meta") or {})
            update: dict[str, Any] = {}
            if bad:
                if meta.get("check_status") != c["status"]:
                    meta.setdefault("transitions", []).append({"at": iso, "to": c["status"]})
                meta.update({"check_status": c["status"], "kind": c["kind"], "evidence": c["evidence"],
                             "ok_streak": 0, "first_ok_at": None, "last_seen_at": iso})
            else:
                streak = int(meta.get("ok_streak") or 0) + 1
                first_ok = meta.get("first_ok_at") or iso
                meta.update({"ok_streak": streak, "first_ok_at": first_ok, "last_ok_at": iso})
                span = (now - datetime.fromisoformat(first_ok)).total_seconds()
                if streak >= RECOVERY_OK_STREAK and span >= RECOVERY_MIN_SECONDS:
                    meta.setdefault("transitions", []).append({"at": iso, "to": "resuelto"})
                    update.update({"status": "resuelto", "ended_at": iso})
                elif meta.get("check_status") != "recuperando":
                    meta.setdefault("transitions", []).append({"at": iso, "to": "recuperando"})
                    meta["check_status"] = "recuperando"
            update["meta"] = meta
            try:
                client.table("admin_events").update(update).eq("id", row["id"]).execute()
                row.update(update)
            except Exception:  # noqa: BLE001
                logger.info("health: no se pudo actualizar incidente", exc_info=True)
    return [r for r in by_comp.values() if r.get("status") == "abierto"]


def evaluate(build: Callable[[], tuple[dict, dict]], client_factory: Callable[[], Any] | None = None,
             force: bool = False) -> dict[str, Any]:
    with _lock:
        hit = _cache.get("eval")
        if hit and not force and time.monotonic() - hit[0] < CACHE_SECONDS:
            payload = dict(hit[1])
            payload["cache_age_s"] = round(time.monotonic() - hit[0], 1)
            return payload
    checks_fns, meta = build()
    checks = run_checks(checks_fns, meta)
    incidents: list[dict[str, Any]] = []
    if client_factory is not None:
        try:
            incidents = reconcile_incidents(client_factory(), checks)
        except Exception:  # noqa: BLE001
            logger.info("health: incidentes no disponibles", exc_info=True)
    payload = {"overall": overall(checks), "evaluated_at": _now().isoformat(), "cache_seconds": CACHE_SECONDS,
               "stale_after_s": 180, "checks": checks, "incidents": incidents,
               "recovery_policy": f"{RECOVERY_OK_STREAK} evaluaciones OK seguidas durante al menos {RECOVERY_MIN_SECONDS // 60} min"}
    with _lock:
        _cache["eval"] = (time.monotonic(), payload)
    return {**payload, "cache_age_s": 0.0}
