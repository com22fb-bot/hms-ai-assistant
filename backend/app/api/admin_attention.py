"""Centro de control /admin: «Requiere mi atención» y métricas comerciales reales.

Reglas (ASTRA F2-A/G/I):
- Nada de ceros ficticios: una métrica sin fuente es ``pendiente_instrumentacion``;
  una consulta que falla es ``error_consulta`` (valor ``None``), nunca 0.
- Solo lectura. Sin cuerpos de correo ni secretos en la respuesta.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter

from app.api.admin_ops import _require_admin
from app.database.supabase import get_supabase_client
from app.services.vendor_payments import PAID, vendor_payment_items

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])

SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

PENDING = "pendiente_instrumentacion"
REAL = "real"
QUERY_ERROR = "error_consulta"


def _metric(value: Any, status: str, source: str, note: str = "") -> dict[str, Any]:
    return {"value": value, "status": status, "source": source, "note": note}


def _pending(note: str) -> dict[str, Any]:
    return _metric(None, PENDING, "sin fuente", note)


def count_or_error(client: Any, table: str, *, eq: dict[str, str] | None = None,
                   in_: dict[str, list[str]] | None = None,
                   gte: dict[str, str] | None = None) -> tuple[int | None, str | None]:
    """(conteo, None) o (None, motivo). Un fallo NUNCA se convierte en 0."""
    try:
        query = client.table(table).select("id", count="exact")
        for column, value in (eq or {}).items():
            query = query.eq(column, value)
        for column, values in (in_ or {}).items():
            query = query.in_(column, values)
        for column, value in (gte or {}).items():
            query = query.gte(column, value)
        response = query.limit(1).execute()
    except Exception as error:  # noqa: BLE001
        logger.info("admin attention count fail %s", table, exc_info=True)
        return None, type(error).__name__
    count = getattr(response, "count", None)
    if count is None:
        return None, "sin_conteo"
    return int(count), None


def commercial_metrics(client: Any) -> dict[str, Any]:
    users, users_err = count_or_error(client, "profiles")
    boxes, boxes_err = count_or_error(client, "communication_accounts", eq={"status": "active"})
    reauth, reauth_err = count_or_error(
        client, "communication_accounts", eq={"status": "needs_reauth"}
    )

    def real_or_error(value: int | None, err: str | None, source: str) -> dict[str, Any]:
        if err is not None:
            return _metric(None, QUERY_ERROR, source, f"Error de consulta ({err})")
        return _metric(value, REAL, source)

    stripe_note = (
        "Stripe no está activado (sin cuenta). Se instrumenta cuando el "
        "propietario active los cobros."
    )
    return {
        "users": real_or_error(users, users_err, "supabase.profiles"),
        "mailboxes_active": real_or_error(boxes, boxes_err, "supabase.communication_accounts[status=active]"),
        "mailboxes_needs_reauth": real_or_error(
            reauth, reauth_err, "supabase.communication_accounts[status=needs_reauth]"
        ),
        "trials_active": _pending(stripe_note),
        "subscriptions_active": _pending(stripe_note),
        "mrr_cents": _pending(stripe_note),
        "arr_cents": _pending(stripe_note),
        "payments_confirmed": _pending(stripe_note),
        "conversion_funnel": _pending("Sin analítica de visitas→registro instrumentada."),
        "feedback_open": _pending("El registro de quejas aún no tiene tabla propia."),
        "signed_up_no_product_use_24h": _pending("Sin evento de primer uso instrumentado."),
    }


def attention_items(client: Any, *, now: datetime | None = None) -> list[dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    items: list[dict[str, Any]] = []

    def query_failed(component: str, err: str) -> None:
        items.append({
            "id": f"query-error:{component}",
            "severity": "medium",
            "category": "monitorizacion",
            "title": f"No se pudo verificar: {component}",
            "detail": f"Error de consulta ({err}). No significa que esté bien ni mal.",
            "action": "Revisar Bitácora / logs del backend.",
            "owner": "técnico",
            "due_at": None,
            "source": component,
        })

    # 1) Incidentes abiertos del sistema.
    try:
        rows = (
            client.table("system_incidents")
            .select("id,incident_code,component,severity,summary,status,occurred_at")
            .in_("status", ["open", "investigating"])
            .order("occurred_at", desc=True)
            .limit(20)
            .execute()
        ).data or []
        for row in rows:
            items.append({
                "id": f"incident:{row.get('id')}",
                "severity": row.get("severity") or "medium",
                "category": "incidente",
                "title": f"{row.get('component')}: {row.get('summary')}",
                "detail": f"{row.get('incident_code')} · estado {row.get('status')}",
                "action": "Diagnosticar y resolver; registrar causa raíz.",
                "owner": "técnico",
                "due_at": None,
                "detected_at": row.get("occurred_at"),
                "source": "supabase.system_incidents",
            })
    except Exception as error:  # noqa: BLE001
        query_failed("system_incidents", type(error).__name__)

    # 2) Buzones que piden reconectar.
    count, err = count_or_error(client, "communication_accounts", eq={"status": "needs_reauth"})
    if err:
        query_failed("communication_accounts", err)
    elif count:
        items.append({
            "id": "mailboxes:needs_reauth",
            "severity": "high",
            "category": "buzones",
            "title": f"{count} buzón(es) requieren volver a conectar",
            "detail": "El permiso OAuth expiró o fue revocado; no se sincronizan.",
            "action": "Avisar al usuario para reconectar desde Ajustes.",
            "owner": "propietario",
            "due_at": None,
            "source": "supabase.communication_accounts",
        })

    # 3) Sincronizaciones fallidas en las últimas 24 h.
    since = (now - timedelta(hours=24)).isoformat()
    count, err = count_or_error(
        client, "gmail_sync_jobs", eq={"status": "failed"}, gte={"created_at": since}
    )
    if err:
        query_failed("gmail_sync_jobs", err)
    elif count:
        items.append({
            "id": "sync:failed_24h",
            "severity": "medium",
            "category": "sincronizacion",
            "title": f"{count} sincronización(es) fallida(s) en 24 h",
            "detail": "Trabajos gmail_sync_jobs con estado failed.",
            "action": "Revisar el error del trabajo y reintentar.",
            "owner": "técnico",
            "due_at": None,
            "source": "supabase.gmail_sync_jobs",
        })

    # 4) Mensajes de contacto sin atender.
    count, err = count_or_error(client, "contact_messages", eq={"status": "nuevo"})
    if err:
        query_failed("contact_messages", err)
    elif count:
        items.append({
            "id": "contact:nuevo",
            "severity": "low",
            "category": "clientes",
            "title": f"{count} mensaje(s) de contacto sin atender",
            "detail": "Formulario público de contacto.",
            "action": "Responder desde la pestaña Mensajes.",
            "owner": "propietario",
            "due_at": None,
            "source": "supabase.contact_messages",
        })

    # 5) Pagos a proveedores por vencer (semáforo).
    items.extend(vendor_payment_items(now))

    # 6) Decisiones del propietario registradas (fijas, explícitas, no métricas).
    items.append({
        "id": "decision:stripe",
        "severity": "info",
        "category": "decision_propietario",
        "title": "Activar cobros (Stripe) — pendiente de tu decisión",
        "detail": "Sin cuenta Stripe; MRR/ARR y pagos muestran «Pendiente de instrumentación».",
        "action": "Decidir cuándo activar cobros. No se crea nada sin tu autorización.",
        "owner": "propietario",
        "due_at": None,
        "source": "roadmap",
    })
    items.append({
        "id": "decision:retencion",
        "severity": "info",
        "category": "decision_propietario",
        "title": "Política de retención de datos — pendiente de tu decisión",
        "detail": "Bloquea la política de adjuntos (F3) y la depuración de datos.",
        "action": "Aprobar plazos de retención.",
        "owner": "propietario",
        "due_at": None,
        "source": "roadmap",
    })

    items.sort(key=lambda it: (SEVERITY_RANK.get(str(it["severity"]), 5), it["due_at"] or "9999"))
    return items


@router.get("/attention")
def admin_attention() -> dict[str, Any]:
    _require_admin()
    client = get_supabase_client()
    now = datetime.now(timezone.utc)
    return {
        "generated_at": now.isoformat(),
        "items": attention_items(client, now=now),
        "commercial": commercial_metrics(client),
        "expenses": PAID,
    }
