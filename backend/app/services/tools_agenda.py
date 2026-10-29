"""Agenda de herramientas de /admin: plan, límites, uso real, costo y vencimientos.

Fuente única: la configuración de abajo + PLAN_LIMITS/CURRENT_PLANS (vendor_payments).
Al cambiar de plan en cualquier plataforma se edita AQUÍ (y CURRENT_PLANS); el panel,
el semáforo y el checklist diario del respaldo lo toman de este módulo.

Montos SIEMPRE en US$ + tipo de cambio (FIX Banxico, con fecha) + MXN.
Semáforo de vencimiento: rojo vencido, amarillo <= 7 días, verde > 7 días.
Semáforo de uso: amarillo >= 70 %, rojo >= 90 %. Sin datos personales ni secretos.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.services.vendor_payments import WARN_DAYS, plan_limits

FX_USD_MXN = 18.81
FX_DATE = "2026-10-29"
FX_SOURCE = "FIX Banxico"
USE_WARN_PCT = 70.0
USE_CRIT_PCT = 90.0

# kind: "pago" (cobro recurrente), "renovacion" (dominio), "token" (secreto que vence).
TOOLS: list[dict[str, Any]] = [
    {"id": "railway", "name": "Railway", "plan": "Hobby", "cost_usd": 5.00, "period": "mensual",
     "limits": "48 vCPU · 48 GB RAM por servicio · 7 días de logs · US$5 de uso incluido",
     "dates": [{"label": "Cobro Hobby", "on": "2026-11-15", "kind": "pago", "estimated": True}]},
    {"id": "cursor", "name": "Cursor", "plan": "Pro (incluye Grok Bot)", "cost_usd": 20.00, "period": "mensual",
     "limits": "Uso incluido del plan Pro",
     "dates": [{"label": "Renovación Pro", "on": "2026-11-07", "kind": "pago", "estimated": True}]},
    {"id": "supabase", "name": "Supabase", "plan": "Free", "cost_usd": 0.0, "period": "mensual",
     "limits": "BD 500 MB · Storage 1 GB · 50,000 MAU · pausa tras 7 días sin actividad", "dates": []},
    {"id": "cloudflare", "name": "Cloudflare", "plan": "Registrar + R2/Workers Free",
     "cost_usd": 10.46, "period": "anual", "cost_estimated": True,
     "cost_note": "Precio de costo .com en Cloudflare Registrar; el cargo exacto no es legible con el conector (sin permiso Billing Read).",
     "limits": "Dominio donexto.com (auto-renovación activa) · R2 10 GB gratis · Workers 100k req/día",
     "dates": [{"label": "Renovación donexto.com", "on": "2027-08-07", "kind": "renovacion", "estimated": False},
               {"label": "Token API Cloudflare", "on": "2027-10-10", "kind": "token", "estimated": False}]},
    {"id": "github", "name": "GitHub", "plan": "Free · Actions", "cost_usd": 0.0, "period": "mensual",
     "limits": "Actions según plan Free", "dates": []},
    {"id": "chatgpt", "name": "ChatGPT", "plan": "Go", "cost_mxn": 100.00, "period": "mensual",
     "cost_estimated": True, "limits": "Plan Go", "dates": []},
    {"id": "supergrok", "name": "SuperGrok", "plan": "SuperGrok", "cost_usd": 10.00, "period": "unico",
     "limits": "Sin reembolso (confirmado por Héctor)", "dates": []},
    {"id": "resend", "name": "Resend", "plan": "Free", "cost_usd": 0.0, "period": "mensual",
     "limits": "3,000 correos/mes · 100/día", "dates": []},
    {"id": "openai", "name": "OpenAI API", "plan": "Pago por uso", "cost_usd": 0.0, "period": "mensual",
     "limits": "Sin cargos conocidos (por confirmar en platform.openai.com)", "dates": []},
    {"id": "doppler", "name": "Doppler", "plan": "Free", "cost_usd": 0.0, "period": "mensual", "limits": "Secretos de Donexto", "dates": []},
    {"id": "google", "name": "Google Cloud", "plan": "Gratis", "cost_usd": 0.0, "period": "mensual", "limits": "OAuth Gmail", "dates": []},
    {"id": "azure", "name": "Microsoft Azure", "plan": "Gratis", "cost_usd": 0.0, "period": "mensual",
     "limits": "App de Hotmail/Outlook · vencimiento del secreto de cliente: por confirmar", "dates": []},
    {"id": "yahoo", "name": "Yahoo Developer", "plan": "Gratis", "cost_usd": 0.0, "period": "mensual", "limits": "—", "dates": []},
    {"id": "notion", "name": "Notion", "plan": "Gratis", "cost_usd": 0.0, "period": "mensual", "limits": "—", "dates": []},
    {"id": "slack", "name": "Slack", "plan": "Gratis", "cost_usd": 0.0, "period": "mensual", "limits": "Canal #alertas", "dates": []},
]

_RANK = {"low": 0, "medium": 1, "critical": 2}


def date_severity(on: str, today: date) -> tuple[str, int]:
    days = (date.fromisoformat(on) - today).days
    if days < 0:
        return "critical", days
    return ("medium" if days <= WARN_DAYS else "low"), days


def usage_severity(pct: float | None) -> str | None:
    if pct is None:
        return None
    return "critical" if pct >= USE_CRIT_PCT else "medium" if pct >= USE_WARN_PCT else "low"


def money(tool: dict[str, Any], fx: float = FX_USD_MXN) -> dict[str, Any]:
    if "cost_mxn" in tool:
        mxn = float(tool["cost_mxn"])
        usd = round(mxn / fx, 2)
    else:
        usd = float(tool.get("cost_usd") or 0)
        mxn = round(usd * fx, 2)
    return {"usd": round(usd, 2), "fx": fx, "fx_date": FX_DATE, "fx_source": FX_SOURCE, "mxn": round(mxn, 2),
            "period": tool.get("period"), "estimated": bool(tool.get("cost_estimated")),
            "note": tool.get("cost_note")}


def _pct(used: Any, limit: Any) -> float | None:
    try:
        used_f, limit_f = float(used), float(limit)
    except (TypeError, ValueError):
        return None
    return round(used_f / limit_f * 100, 1) if limit_f > 0 else None


def _usage(tool_id: str, perf: dict[str, Any] | None) -> list[dict[str, Any]]:
    perf = perf or {}
    if tool_id == "railway":
        rw = perf.get("railway") or {}
        if not rw.get("available"):
            return []
        plan = plan_limits("railway")
        return [
            {"label": "CPU", "used": rw.get("cpu_vcpu"), "limit": plan.get("cpu_vcpu"), "unit": "vCPU",
             "pct": _pct(rw.get("cpu_vcpu"), plan.get("cpu_vcpu"))},
            {"label": "RAM", "used": rw.get("memory_gb"), "limit": plan.get("memory_gb"), "unit": "GB",
             "pct": _pct(rw.get("memory_gb"), plan.get("memory_gb"))},
        ]
    if tool_id == "supabase":
        db = perf.get("database") or {}
        if not db.get("available"):
            return []
        size = db.get("db_size_bytes")
        out = [{"label": "BD", "used": round(float(size) / 1048576, 1) if size else None, "limit": 500, "unit": "MB",
                "pct": db.get("used_pct")}]
        if db.get("users_active_30d") is not None:
            out.append({"label": "Usuarios activos 30 d", "used": db.get("users_active_30d"), "limit": 50000,
                        "unit": "MAU", "pct": _pct(db.get("users_active_30d"), 50000)})
        return out
    return []


def build_agenda(today: date, perf: dict[str, Any] | None = None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    monthly_usd = 0.0
    for tool in TOOLS:
        dates = []
        for d in tool.get("dates", []):
            sev, days = date_severity(d["on"], today)
            dates.append({**d, "severity": sev, "days": days})
        usage = _usage(tool["id"], perf)
        for u in usage:
            u["severity"] = usage_severity(u.get("pct"))
        sevs = [d["severity"] for d in dates] + [u["severity"] for u in usage if u.get("severity")]
        worst = max(sevs, key=_RANK.__getitem__) if sevs else "low"
        cost = money(tool)
        if cost["period"] == "mensual":
            monthly_usd += cost["usd"]
        elif cost["period"] == "anual":
            monthly_usd += cost["usd"] / 12
        rows.append({"id": tool["id"], "name": tool["name"], "plan": tool["plan"], "limits": tool["limits"],
                     "usage": usage, "cost": cost, "dates": dates, "severity": worst})
    nxt = sorted((d | {"tool": r["name"]} for r in rows for d in r["dates"] if d["days"] >= 0), key=lambda x: x["days"])
    alerts = [r for r in rows if r["severity"] != "low"]
    return {
        "today": today.isoformat(),
        "fx": {"usd_mxn": FX_USD_MXN, "date": FX_DATE, "source": FX_SOURCE},
        "monthly_fixed": {"usd": round(monthly_usd, 2), "fx": FX_USD_MXN, "mxn": round(monthly_usd * FX_USD_MXN, 2)},
        "next_due": nxt[0] if nxt else None,
        "status": max((r["severity"] for r in rows), key=_RANK.__getitem__) if rows else "low",
        "alerts": [{"tool": r["name"], "severity": r["severity"]} for r in alerts],
        "rows": rows,
    }
