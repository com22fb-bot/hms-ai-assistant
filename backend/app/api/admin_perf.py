"""Panel /admin: Rendimiento (backend, base, seguridad, sitio) y Mis gastos.

Todo exige sesión de un correo en ADMIN_EMAILS. Los datos externos se guardan
60 s en memoria para no gastar cuotas ni hacer lento el panel.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.admin_ops import _require_admin
from app.database.supabase import get_supabase_client
from app.services import health_eval
from app.services.health_eval import classify_provider_error
from app.services.runtime_metrics import snapshot as runtime_snapshot

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])

CACHE_SECONDS = 60
FREE_DB_LIMIT_BYTES = 500 * 1024 * 1024
_cache: dict[str, tuple[float, Any]] = {}
_cache_lock = threading.Lock()


def _cached(key: str, loader: Any) -> Any:
    now = time.monotonic()
    with _cache_lock:
        hit = _cache.get(key)
        if hit and hit[0] > now:
            return hit[1]
    value = loader()
    with _cache_lock:
        _cache[key] = (now + CACHE_SECONDS, value)
    return value


def _missing(var: str, steps: list[str]) -> dict[str, Any]:
    return {"available": False, "status": "falta_token", "variable": var, "steps": steps}


# --- Railway -------------------------------------------------------------------

RAILWAY_STEPS = [
    "En Railway > proyecto grand-nourishment > Settings > Tokens, crea un token de PROYECTO (entorno production) llamado 'donexto-admin-metricas'.",
    "Guárdalo en Doppler donexto/prd como RAILWAY_METRICS_TOKEN y cárgalo en el servicio hms-ai-assistant.",
]

_RAILWAY_QUERY = """
query($p:String!,$s:String!,$e:String!,$d:DateTime!){
  metrics(projectId:$p, serviceId:$s, environmentId:$e, startDate:$d,
          measurements:[CPU_USAGE,CPU_LIMIT,MEMORY_USAGE_GB,MEMORY_LIMIT_GB],
          sampleRateSeconds:900){ measurement values{ ts value } }
  deployments(first:1, input:{projectId:$p, serviceId:$s, environmentId:$e}){
    edges{ node{ id status createdAt meta } } }
}
"""


def _railway_headers() -> dict[str, str] | None:
    """Token de PROYECTO (mínimo: un proyecto/entorno) con su cabecera propia; si no, el de cuenta (Bearer).

    Causa raíz del «Not Authorized» del 23-oct: el RAILWAY_API_TOKEN cargado en Railway era un token viejo
    sin acceso; además un token de proyecto no sirve con 'Authorization: Bearer' (requiere Project-Access-Token).
    """
    project = os.getenv("RAILWAY_METRICS_TOKEN", "").strip()
    if project:
        return {"Project-Access-Token": project}
    account = os.getenv("RAILWAY_API_TOKEN", "").strip()
    return {"Authorization": f"Bearer {account}"} if account else None


def _railway() -> dict[str, Any]:
    headers = _railway_headers()
    base = {
        "region": os.getenv("RAILWAY_REPLICA_REGION", "") or None,
        "replica_id": (os.getenv("RAILWAY_REPLICA_ID", "") or "")[:8] or None,
        "deployment_id": (os.getenv("RAILWAY_DEPLOYMENT_ID", "") or "")[:8] or None,
    }
    if not headers:
        return {**base, **_missing("RAILWAY_METRICS_TOKEN", RAILWAY_STEPS), "kind": "permiso"}
    ids = {
        "p": os.getenv("RAILWAY_PROJECT_ID", ""),
        "s": os.getenv("RAILWAY_SERVICE_ID", ""),
        "e": os.getenv("RAILWAY_ENVIRONMENT_ID", ""),
        "d": (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    try:
        response = httpx.post(
            "https://backboard.railway.com/graphql/v2",
            json={"query": _RAILWAY_QUERY, "variables": ids},
            headers={**headers, "User-Agent": "donexto-admin"},
            timeout=8,
        )
        payload = response.json()
    except Exception as error:
        return {**base, "available": False, "status": "error", "message": type(error).__name__,
                "kind": classify_provider_error(exc=error)}
    if payload.get("errors"):
        # También errores PARCIALES (p. ej. deployments sin permiso): nunca se presentan como "ok".
        message = str(payload["errors"][0].get("message", ""))[:200]
        return {**base, "available": False, "status": "error", "message": message,
                "kind": classify_provider_error(message, response.status_code)}
    data = payload.get("data") or {}
    series = {m["measurement"]: m.get("values") or [] for m in data.get("metrics") or []}

    def last(name: str) -> float | None:
        values = series.get(name) or []
        return float(values[-1]["value"]) if values else None

    def peak(name: str) -> float | None:
        values = series.get(name) or []
        return max(float(v["value"]) for v in values) if values else None

    edges = ((data.get("deployments") or {}).get("edges")) or []
    deploy = edges[0]["node"] if edges else {}
    return {
        **base,
        "available": True,
        "status": "ok",
        "cpu_vcpu": last("CPU_USAGE"),
        "cpu_vcpu_peak_24h": peak("CPU_USAGE"),
        "cpu_limit": last("CPU_LIMIT"),
        "memory_gb": last("MEMORY_USAGE_GB"),
        "memory_gb_peak_24h": peak("MEMORY_USAGE_GB"),
        "memory_limit_gb": last("MEMORY_LIMIT_GB"),
        "cpu_series": [round(float(v["value"]), 4) for v in series.get("CPU_USAGE", [])][-48:],
        "memory_series": [round(float(v["value"]), 3) for v in series.get("MEMORY_USAGE_GB", [])][-48:],
        "last_deploy": {"status": deploy.get("status"), "created_at": deploy.get("createdAt"),
                        "id": (deploy.get("id") or "")[:8] or None,
                        "commit": ((deploy.get("meta") or {}).get("commitHash") or "")[:12] or None},
        "metrics_at": (series.get("MEMORY_USAGE_GB") or [{}])[-1].get("ts") if series.get("MEMORY_USAGE_GB") else None,
    }


# --- Supabase ------------------------------------------------------------------

def _database() -> dict[str, Any]:
    try:
        response = get_supabase_client().rpc("admin_db_stats", {}).execute()
    except Exception as error:
        return {"available": False, "status": "error", "message": type(error).__name__}
    data = response.data if isinstance(response.data, dict) else {}
    if isinstance(response.data, list) and response.data:
        first = response.data[0]
        data = first.get("admin_db_stats", first) if isinstance(first, dict) else {}
    if not data:
        return {"available": False, "status": "error", "message": "admin_db_stats sin datos"}
    size = int(data.get("db_size_bytes") or 0)
    return {
        "available": True,
        "status": "ok",
        **data,
        "plan": "Free",  # verificado 23-oct-2026 con la API de Supabase (organización: plan free)
        "plan_limit_bytes": FREE_DB_LIMIT_BYTES,
        "used_pct": round(size / FREE_DB_LIMIT_BYTES * 100, 1) if size else None,
    }


# --- Cloudflare ----------------------------------------------------------------

CLOUDFLARE_STEPS = [
    "En dash.cloudflare.com > Mi perfil > API Tokens > Create Token > Custom token.",
    "Nombre 'donexto-admin-analytics'. Permiso: Zone > Analytics > Read. Recursos: Include > Specific zone > donexto.com.",
    "En Railway (servicio hms-ai-assistant > Variables) agrega CLOUDFLARE_ANALYTICS_TOKEN con ese valor y CLOUDFLARE_ZONE_ID = eda5f4b6a2afa1ab6c1603f2602397be.",
]

_CF_QUERY = """
query($z:String!,$d:Date!){ viewer{ zones(filter:{zoneTag:$z}){
  httpRequests1dGroups(limit:7, filter:{date_geq:$d}, orderBy:[date_ASC]){
    dimensions{ date } sum{ requests cachedRequests threats bytes cachedBytes } } } } }
"""


def _cloudflare() -> dict[str, Any]:
    token = os.getenv("CLOUDFLARE_ANALYTICS_TOKEN", "").strip()
    zone = os.getenv("CLOUDFLARE_ZONE_ID", "").strip()
    if not token or not zone:
        return _missing("CLOUDFLARE_ANALYTICS_TOKEN", CLOUDFLARE_STEPS)
    try:
        response = httpx.post(
            "https://api.cloudflare.com/client/v4/graphql",
            json={"query": _CF_QUERY, "variables": {"z": zone, "d": (date.today() - timedelta(days=6)).isoformat()}},
            headers={"Authorization": f"Bearer {token}"},
            timeout=8,
        )
        payload = response.json()
    except Exception as error:
        return {"available": False, "status": "error", "message": type(error).__name__}
    if payload.get("errors"):
        return {"available": False, "status": "error", "message": str(payload["errors"][0].get("message", ""))[:200]}
    zones = (((payload.get("data") or {}).get("viewer") or {}).get("zones")) or []
    days = (zones[0].get("httpRequests1dGroups") if zones else None) or []
    rows = [{"date": d["dimensions"]["date"], **d["sum"]} for d in days]
    total = sum(r["requests"] for r in rows)
    cached = sum(r["cachedRequests"] for r in rows)
    return {
        "available": True,
        "status": "ok",
        "days": rows,
        "requests_7d": total,
        "threats_7d": sum(r["threats"] for r in rows),
        "cached_pct": round(cached / total * 100, 1) if total else None,
        "period": "7 días naturales UTC (incluye hoy parcial)",
        "today": rows[-1] if rows else None,
    }


# --- Sitio ---------------------------------------------------------------------

SITE_CHECKS = [
    ("Landing", "https://www.donexto.com/"),
    ("App", "https://app.donexto.com/"),
    ("API /health", "https://app.donexto.com/api/hms/health"),
    ("Admin", "https://www.donexto.com/admin"),
]


def _check(label: str, url: str) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        response = httpx.get(url, timeout=10, follow_redirects=False,
                             headers={"user-agent": "donexto-admin-uptime/1.0"})
        status = response.status_code
    except Exception as error:
        return {"label": label, "url": url, "ok": False, "status": None,
                "ms": None, "message": type(error).__name__}
    return {"label": label, "url": url, "ok": 200 <= status < 400, "status": status,
            "ms": round((time.perf_counter() - started) * 1000)}


def _sites() -> list[dict[str, Any]]:
    with ThreadPoolExecutor(max_workers=len(SITE_CHECKS)) as pool:
        return list(pool.map(lambda item: _check(*item), SITE_CHECKS))


def _performance_payload() -> dict[str, Any]:
    with ThreadPoolExecutor(max_workers=4) as pool:
        railway = pool.submit(_railway)
        database = pool.submit(_database)
        cloudflare = pool.submit(_cloudflare)
        sites = pool.submit(_sites)
        result = {
            "railway": railway.result(),
            "database": database.result(),
            "cloudflare": cloudflare.result(),
            "sites": sites.result(),
        }
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    return result


def _health_build() -> tuple[dict, dict]:
    client = get_supabase_client()
    snap = runtime_snapshot()
    fns = {
        "api": lambda: health_eval.result("api", "API del backend", True, "ok", "ok",
                                          f"Proceso activo {snap['uptime_seconds']} s", data_at=datetime.now(timezone.utc).isoformat(),
                                          source="este proceso en Railway"),
        "database": lambda: health_eval.check_database(client),
        "config": health_eval.check_config,
        "backup": lambda: health_eval.check_backup(client),
        "frontend": lambda: health_eval.check_site("frontend", "App (app.donexto.com)", "https://app.donexto.com/", True),
        "landing": lambda: health_eval.check_site("landing", "Landing (www.donexto.com)", "https://www.donexto.com/", False),
        "db_quota": lambda: health_eval.check_db_quota(client),
        "errors": lambda: health_eval.check_errors(snap),
        "railway": lambda: health_eval.check_railway(lambda: _cached("railway", _railway)),
        "cloudflare": lambda: health_eval.check_cloudflare(lambda: _cached("cloudflare", _cloudflare)),
    }
    meta = {"api": ("API del backend", True), "database": ("Base de datos (Supabase)", True),
            "config": ("Autenticación y configuración crítica", True), "backup": ("Respaldo diario", True),
            "frontend": ("App (app.donexto.com)", True), "landing": ("Landing (www.donexto.com)", False),
            "db_quota": ("Espacio de base", False), "errors": ("Errores recientes del backend", False),
            "railway": ("Railway (métricas y despliegue)", False), "cloudflare": ("Cloudflare (analítica)", False)}
    return fns, meta


@router.get("/health")
def admin_health(force: bool = False) -> dict[str, Any]:
    """Evaluación única de salud (semáforo de /admin y base del futuro Centro de control)."""
    _require_admin()
    return health_eval.evaluate(_health_build, get_supabase_client, force=force)


@router.get("/performance")
def admin_performance() -> dict[str, Any]:
    _require_admin()
    payload = dict(_cached("performance", _performance_payload))
    # Las métricas del propio proceso son baratas: siempre al momento.
    payload["process"] = runtime_snapshot()
    payload["cache_seconds"] = CACHE_SECONDS
    # Cada tarjeta muestra su estado desde la MISMA evaluación del semáforo (no colores propios).
    try:
        payload["health"] = health_eval.evaluate(_health_build, get_supabase_client)
    except Exception:  # noqa: BLE001
        payload["health"] = None
    return payload


# --- Mis gastos ----------------------------------------------------------------

Periodicity = Literal["mensual", "anual", "unico"]


class ExpenseIn(BaseModel):
    servicio: str = Field(min_length=1, max_length=120)
    plan: str = Field(default="", max_length=120)
    monto: float = Field(default=0, ge=0, le=1_000_000)
    moneda: Literal["USD", "MXN"] = "USD"
    periodicidad: Periodicity = "mensual"
    proximo_cobro: date | None = None
    notas: str = Field(default="", max_length=1000)
    activo: bool = True


class FxIn(BaseModel):
    usd_mxn: float = Field(gt=0, le=1000)


def _rows(response: Any) -> list[dict[str, Any]]:
    data = getattr(response, "data", None)
    return [row for row in data if isinstance(row, dict)] if isinstance(data, list) else []


def _usd_mxn() -> float:
    rows = _rows(get_supabase_client().table("admin_settings").select("value").eq("key", "usd_mxn").limit(1).execute())
    try:
        return float(rows[0]["value"]) if rows else 18.5
    except (TypeError, ValueError):
        return 18.5


def monthly_usd(expense: dict[str, Any], usd_mxn: float) -> float:
    if not expense.get("activo"):
        return 0.0
    amount = float(expense.get("monto") or 0)
    if expense.get("moneda") == "MXN":
        amount = amount / usd_mxn if usd_mxn else 0.0
    period = expense.get("periodicidad")
    if period == "anual":
        return amount / 12
    if period == "unico":
        return 0.0
    return amount


def summarize_expenses(rows: list[dict[str, Any]], usd_mxn: float, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    horizon = today + timedelta(days=30)
    total = round(sum(monthly_usd(row, usd_mxn) for row in rows), 2)
    upcoming = []
    for row in rows:
        raw = row.get("proximo_cobro")
        if not raw or not row.get("activo"):
            continue
        try:
            when = date.fromisoformat(str(raw)[:10])
        except ValueError:
            continue
        if today <= when <= horizon:
            upcoming.append({"id": row.get("id"), "servicio": row.get("servicio"),
                             "monto": row.get("monto"), "moneda": row.get("moneda"),
                             "proximo_cobro": when.isoformat()})
    upcoming.sort(key=lambda item: item["proximo_cobro"])
    return {"monthly_usd": total, "monthly_mxn": round(total * usd_mxn, 2),
            "usd_mxn": usd_mxn, "upcoming_30d": upcoming}


def _expense_payload(payload: ExpenseIn) -> dict[str, Any]:
    data = payload.model_dump()
    data["proximo_cobro"] = payload.proximo_cobro.isoformat() if payload.proximo_cobro else None
    return data


@router.get("/expenses")
def admin_list_expenses() -> dict[str, Any]:
    _require_admin()
    rows = _rows(
        get_supabase_client().table("admin_expenses").select("*")
        .order("activo", desc=True).order("servicio").execute()
    )
    return {"expenses": rows, **summarize_expenses(rows, _usd_mxn())}


@router.post("/expenses")
def admin_create_expense(payload: ExpenseIn) -> dict[str, Any]:
    _require_admin()
    rows = _rows(get_supabase_client().table("admin_expenses").insert(_expense_payload(payload)).execute())
    if not rows:
        raise HTTPException(status_code=503, detail="Supabase no confirmó el gasto.")
    return {"expense": rows[0]}


@router.put("/expenses/{expense_id}")
def admin_update_expense(expense_id: str, payload: ExpenseIn) -> dict[str, Any]:
    _require_admin()
    data = {**_expense_payload(payload), "updated_at": datetime.now(timezone.utc).isoformat()}
    rows = _rows(get_supabase_client().table("admin_expenses").update(data).eq("id", expense_id).execute())
    if not rows:
        raise HTTPException(status_code=404, detail="Gasto no encontrado.")
    return {"expense": rows[0]}


@router.delete("/expenses/{expense_id}")
def admin_delete_expense(expense_id: str) -> dict[str, Any]:
    _require_admin()
    get_supabase_client().table("admin_expenses").delete().eq("id", expense_id).execute()
    return {"status": "ok"}


@router.put("/expenses-settings")
def admin_update_fx(payload: FxIn) -> dict[str, Any]:
    _require_admin()
    get_supabase_client().table("admin_settings").upsert(
        {"key": "usd_mxn", "value": str(payload.usd_mxn),
         "updated_at": datetime.now(timezone.utc).isoformat()},
        on_conflict="key",
    ).execute()
    return {"usd_mxn": payload.usd_mxn}
