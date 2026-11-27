"""Agenda de pagos y vencimientos para la vista principal de /admin.

Une, en vivo y en hora de Ciudad de México:
- ``public.admin_expenses`` (Mis gastos) y ``admin_settings.usd_mxn`` (TC);
- fechas de renovación y llaves de ``tools_agenda.TOOLS``.

Semáforo (mismo criterio que la imagen aprobada por Héctor el 27-nov-2026):
- ``rojo``: vencido o vence en 3 días o menos;
- ``naranja``: 4 a 14 días;
- ``verde``: 15 a 60 días;
- ``luego``: más de 60 días («Más adelante»).

Montos siempre en US$ + MXN con el TC usado. Sin datos personales ni secretos.
Donexto no usa n8n y la llave GITHUB_TOKEN_DONEXTO dejó de usarse: ambos se excluyen.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.services.tools_agenda import FX_DATE, FX_SOURCE, FX_USD_MXN, TOOLS

CDMX = ZoneInfo("America/Mexico_City")
TIMELINE_DAYS = 60
SEVERITY_ORDER = ("rojo", "naranja", "verde", "luego")
SEVERITY_LABEL = {
    "rojo": "Vencido o en 3 días",
    "naranja": "En 4–14 días",
    "verde": "En 15–60 días",
    "luego": "Más adelante",
}
_EXCLUDED_LABEL = re.compile(r"GITHUB_TOKEN_DONEXTO", re.I)
_TIPO = {"pago": "pago", "renovacion": "renovación", "renovación": "renovación", "token": "llave", "llave": "llave"}
_EST_DATE = re.compile(
    r"(renovaci[oó]n|fecha|cobro|pr[oó]xim[ao]).{0,48}estimad|estimad[ao].{0,48}(renovaci|el \d+)", re.I)
_EST_COST = re.compile(r"costo.{0,40}estimad|estimad.{0,20}(precio|costo|cargo)", re.I)


def today_cdmx(now: datetime | None = None) -> date:
    moment = now or datetime.now(CDMX)
    if moment.tzinfo is None:
        return moment.date()
    return moment.astimezone(CDMX).date()


def severity_of(days: int) -> str:
    if days <= 3:
        return "rojo"
    if days <= 14:
        return "naranja"
    if days <= TIMELINE_DAYS:
        return "verde"
    return "luego"


def money_pair(amount: float, currency: str, fx: float) -> tuple[float, float]:
    if (currency or "USD").upper() == "MXN":
        return (round(amount / fx, 2) if fx else 0.0), round(amount, 2)
    return round(amount, 2), round(amount * fx, 2)


def _norm(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip().lower()).replace("dominio donexto.com", "donexto.com")


def _excluded(name: str, extra: str = "") -> bool:
    return "n8n" in _norm(name) or bool(_EXCLUDED_LABEL.search(f"{name} {extra}"))


def _parse_day(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _tipo_from_expense(period: str, servicio: str) -> str:
    s = servicio.lower()
    if "token" in s or "llave" in s:
        return "llave"
    if "dominio" in s or period.lower() == "anual":
        return "renovación"
    return "pago"


def _action_for(servicio: str, estimated: bool) -> str:
    s = servicio.lower()
    if estimated and "cursor" in s:
        return "Confirmar fecha en cursor.com/dashboard"
    if estimated and "chatgpt" in s:
        return "Confirmar renovación del plan Go"
    if "railway" in s:
        return "Verificar fondos antes del cobro"
    return ""


def build_payments_agenda(expenses: list[dict[str, Any]], fx_setting: float | None,
                          today: date, generated_at: datetime | None = None) -> dict[str, Any]:
    """Pendientes de pago/vencimiento con días restantes y semáforo, más el gasto mensual."""
    fx = float(fx_setting) if fx_setting and fx_setting > 0 else FX_USD_MXN
    fx_from_settings = bool(fx_setting and fx_setting > 0)
    items: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    def add(item: dict[str, Any]) -> None:
        key = (_norm(item["servicio"]), item["on"], item["label"] if item["tipo"] == "llave" else item["tipo"])
        if key in seen:
            return
        seen.add(key)
        on = date.fromisoformat(item["on"])
        days = (on - today).days
        item["days"] = days
        item["severity"] = severity_of(days)
        items.append(item)

    for row in expenses:
        if row.get("activo") is False:
            continue
        servicio = str(row.get("servicio") or "").strip()
        notas = str(row.get("notas") or "")
        if not servicio or _excluded(servicio, notas):
            continue
        on = _parse_day(row.get("proximo_cobro"))
        if on is None:
            continue
        try:
            amount = float(row.get("monto") or 0)
        except (TypeError, ValueError):
            amount = 0.0
        usd, mxn = money_pair(amount, str(row.get("moneda") or "USD"), fx)
        estimated = bool(_EST_DATE.search(notas))
        period = str(row.get("periodicidad") or "")
        add({
            "id": f"gasto:{row.get('id') or servicio}:{on.isoformat()}",
            "servicio": servicio, "tipo": _tipo_from_expense(period, servicio), "on": on.isoformat(),
            "usd": usd, "mxn": mxn, "currency": str(row.get("moneda") or "USD").upper(),
            "estimated": estimated, "cost_estimated": bool(_EST_COST.search(notas)),
            "period": period, "label": str(row.get("plan") or ""),
            "action": _action_for(servicio, estimated), "source": "admin_expenses",
        })

    for tool in TOOLS:
        name = str(tool.get("name") or "").strip()
        if "cost_mxn" in tool:
            usd, mxn = money_pair(float(tool.get("cost_mxn") or 0), "MXN", fx)
            currency = "MXN"
        else:
            usd, mxn = money_pair(float(tool.get("cost_usd") or 0), "USD", fx)
            currency = "USD"
        for d in tool.get("dates") or []:
            on = _parse_day(d.get("on"))
            label = str(d.get("label") or "")
            if on is None or _excluded(name, label):
                continue
            tipo = _TIPO.get(str(d.get("kind") or "pago"), "pago")
            if tipo == "renovación" and any(
                x["tipo"] == "renovación" and x["on"] == on.isoformat() and (
                    _norm(x["servicio"]).split()[-1] == _norm(name).split()[-1]
                    or ("donexto.com" in label.lower() and "donexto.com" in _norm(x["servicio"]))
                ) for x in items
            ):
                continue
            if tipo == "pago" and any(
                _norm(x["servicio"]).split()[-1] == _norm(name).split()[-1] and x["on"] == on.isoformat()
                and x["tipo"] == "pago" for x in items
            ):
                continue
            servicio = "Dominio donexto.com" if tipo == "renovación" and "donexto.com" in label.lower() else name
            is_key = tipo == "llave"
            key_label = label
            if is_key:
                key_label = re.sub(r"^Token\s+", "", label.split("(")[0].strip())
                key_label = re.sub(re.escape(name), "", key_label, flags=re.I).strip() or "llave"
            add({
                "id": f"agenda:{tool.get('id')}:{on.isoformat()}:{key_label}",
                "servicio": servicio, "tipo": tipo, "on": on.isoformat(),
                "usd": 0.0 if is_key else usd, "mxn": 0.0 if is_key else mxn, "currency": currency,
                "estimated": bool(d.get("estimated")),
                "cost_estimated": bool(tool.get("cost_estimated")) and not is_key,
                "period": str(tool.get("period") or ""), "label": key_label,
                "action": "Sin costo · no es una licencia" if is_key else "", "source": "tools_agenda",
            })

    items.sort(key=lambda x: (x["on"], x["servicio"]))

    parts: list[dict[str, Any]] = []
    notes: list[str] = []
    for row in expenses:
        servicio = str(row.get("servicio") or "").strip()
        if row.get("activo") is False or not servicio or _excluded(servicio):
            continue
        period = str(row.get("periodicidad") or "mensual").lower()
        if period in {"unico", "único"}:
            continue
        try:
            amount = float(row.get("monto") or 0)
        except (TypeError, ValueError):
            continue
        usd, _ = money_pair(amount, str(row.get("moneda") or "USD"), fx)
        if usd <= 0:
            continue
        if period == "anual":
            usd = usd / 12
        elif period != "mensual":
            notes.append(f"{servicio}: periodicidad «{period}» fuera del total mensual.")
            continue
        parts.append({"servicio": servicio, "usd": round(usd, 2), "mxn": round(usd * fx, 2)})
    parts.sort(key=lambda p: -p["usd"])
    total_usd = round(sum(p["usd"] for p in parts), 2)

    counts = {sev: sum(1 for it in items if it["severity"] == sev) for sev in SEVERITY_ORDER}
    overdue = sum(1 for it in items if it["days"] < 0)
    if overdue:
        headline = f"{overdue} vencido(s)"
    elif counts["rojo"]:
        headline = f"{counts['rojo']} por vencer en 3 días o menos"
    else:
        headline = "Nada vencido ni por vencer en 3 días"

    return {
        "today": today.isoformat(),
        "timezone": "America/Mexico_City",
        "generated_at": (generated_at or datetime.now(CDMX)).isoformat(),
        "timeline_days": TIMELINE_DAYS,
        "headline": headline,
        "status": next((s for s in ("rojo", "naranja", "verde") if counts[s]), "verde"),
        "counts": counts,
        "severity_labels": SEVERITY_LABEL,
        "fx": {"usd_mxn": fx, "source": "Mis gastos (admin_settings)" if fx_from_settings else FX_SOURCE,
               "date": None if fx_from_settings else FX_DATE},
        "items": items,
        "monthly": {"usd": total_usd, "mxn": round(total_usd * fx, 2), "fx": fx, "parts": parts},
        "notes": notes,
    }
