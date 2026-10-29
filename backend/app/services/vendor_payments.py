"""Gastos fijos de proveedores de Donexto y su semáforo de vencimiento en /admin.

Registro manual (config en código, sin datos personales ni secretos). Cada pago
confirmado se agrega a ``PAID`` y el siguiente vencimiento a ``UPCOMING``.

Semáforo (hora CDMX no importa: se compara por fecha UTC del vencimiento):
- rojo   (critical): vencido.
- amarillo (medium): faltan <= 7 días.
- verde  (low): faltan más de 7 días.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

WARN_DAYS = 7

PAID: list[dict[str, Any]] = [
    {
        "vendor": "Railway",
        "concept": "Plan Hobby (backend api.donexto.com) · periodo 15-oct a 15-nov-2026",
        "invoice": "4CQV4X3R-0002",
        "amount_usd": 5.00,
        "paid_on": "2026-10-29",
        "note": "Uso real del mes anterior US$1.85, cubierto por el crédito incluido.",
    },
    {
        "vendor": "Cursor",
        "concept": "Plan Pro (incluye Grok Bot) · periodo 7-oct a 7-nov-2026",
        "invoice": "",
        "amount_usd": 20.00,
        "paid_on": "2026-10-07",
        "note": "Fecha de pago según registro del proyecto; confirmar recibo en cursor.com/dashboard.",
    },
]

UPCOMING: list[dict[str, Any]] = [
    {
        "vendor": "Railway",
        "concept": "Plan Hobby · periodo 15-nov a 15-dic-2026",
        "amount_usd": 5.00,
        "due_on": "2026-11-15",
        "estimated": True,
    },
    {
        "vendor": "Cursor",
        "concept": "Plan Pro (incluye Grok Bot) · renovación mensual; fecha estimada por el pago del 7-oct, por confirmar",
        "amount_usd": 20.00,
        "due_on": "2026-11-07",
        "estimated": True,
    },
]


def payment_status(due_on: str, today: date) -> tuple[str, int]:
    days = (date.fromisoformat(due_on) - today).days
    if days < 0:
        return "critical", days
    if days <= WARN_DAYS:
        return "medium", days
    return "low", days


def vendor_payment_items(now: datetime | None = None,
                         upcoming: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    today = (now or datetime.now(timezone.utc)).date()
    items: list[dict[str, Any]] = []
    for pay in UPCOMING if upcoming is None else upcoming:
        try:
            severity, days = payment_status(str(pay["due_on"]), today)
            amount = float(pay["amount_usd"])
        except (KeyError, TypeError, ValueError):
            items.append({
                "id": f"pago:invalido:{pay.get('vendor', '?')}",
                "severity": "medium", "category": "pagos",
                "title": f"Pago mal registrado: {pay.get('vendor', '?')}",
                "detail": "Falta fecha o monto válido.", "action": "Corregir vendor_payments.py.",
                "owner": "técnico", "due_at": None, "source": "vendor_payments",
            })
            continue
        if days < 0:
            when = f"VENCIDO hace {-days} día(s)"
        elif days == 0:
            when = "vence HOY"
        else:
            when = f"vence en {days} día(s)"
        approx = "~" if pay.get("estimated") else ""
        items.append({
            "id": f"pago:{pay['vendor']}:{pay['due_on']}",
            "severity": severity,
            "category": "pagos",
            "title": f"{pay['vendor']}: {approx}US${amount:.2f} {when} ({pay['due_on']})",
            "detail": str(pay.get("concept", "")),
            "action": "Confirmar fondos en la tarjeta y registrar el comprobante.",
            "owner": "propietario",
            "due_at": f"{pay['due_on']}T00:00:00+00:00",
            "source": "vendor_payments",
        })
    return items


# --- Planes contratados: fuente única de límites por plataforma -------------------
# Al cambiar de plan, edita CURRENT_PLANS; /admin (Rendimiento) toma los límites de aquí.
PLAN_LIMITS: dict[str, dict[str, dict[str, Any]]] = {
    "railway": {
        "Trial": {"cpu_vcpu": 2, "memory_gb": 1, "replicas": 1, "log_days": 3, "included_usd": 5},
        "Hobby": {"cpu_vcpu": 48, "memory_gb": 48, "replicas": 6, "log_days": 7, "included_usd": 5},
        "Pro": {"cpu_vcpu": 1000, "memory_gb": 1000, "replicas": 42, "log_days": 30, "included_usd": 20},
    },
}
CURRENT_PLANS: dict[str, str] = {"railway": "Hobby"}


def plan_limits(platform: str) -> dict[str, Any]:
    """Plan vigente y sus límites; {} si la plataforma o el plan no están registrados."""
    name = CURRENT_PLANS.get(platform)
    limits = PLAN_LIMITS.get(platform, {}).get(name or "")
    return {"plan": name, **limits} if limits else {}
