"""Taxonomía v1 aprobada por Héctor (13-oct-2026). Solo la usa el cerebro v1 (BRAIN_V1_ENABLED).

Un área principal por correo + etiquetas secundarias. Las 16 áreas base son las de import_categories.CATEGORY_IDS
(13 áreas + social + promos + other). Ver docs/TAXONOMIA_V1.md.
"""
from __future__ import annotations

import re
from typing import Any

# Regla del cerebro → área principal (cuando la regla define el área sin dudas).
RULE_AREA = {
    "security": "security", "security_action": "security", "security_unverified": "security", "phishing_suspect": "security",
    "verification": "security",
    "invoice_due": "bills", "charge_due": "bills", "bill_followup": "bills", "bill_settled": "bills", "invoice_info": "bills",
    "payment_confirmation": "bills", "partial_payment": "bills",  # pago de una obligación: vive con la factura
    "booking": "travel", "booking_pending": "travel", "booking_cancel": "travel",
    "appointment": "agenda", "appointment_cancel": "agenda",
    "renewal_upcoming": "subscriptions", "renewal_done": "subscriptions", "renewal_action": "subscriptions",
    "order_notice": "orders", "stock_alert": "promos", "promotional": "promos", "social": "social",
}
_EVENT_RE = re.compile(r"(evento|concierto|conferencia|partido|funcion|entrada|boletos?|event|concert|tickets?)")
_TRAVEL_RE = re.compile(r"(vuelo|flight|hotel|hospedaje|itinerario|itinerary|aerolinea|check-?in)")
_MONEY_RE = re.compile(r"(deposito|transferencia|spei|retiro|movimiento|cargo .{0,20}tarjeta|compra .{0,30}tarjeta|deposit|transfer)")
_INSURANCE_RE = re.compile(r"(seguro|poliza|aseguradora|insurance|policy)")
_TOPIC_AREAS = ("health", "government", "education", "work", "home", "insurance", "money", "orders", "subscriptions",
                "travel", "agenda", "bills")


def classify_area(rule: str, text: str, sender: str, confidence: float) -> dict[str, Any]:
    """Devuelve {"area": principal, "tags": secundarias}. Seguridad y Facturas nunca se ocultan ni se sobrescriben."""
    from app.services.import_categories import import_category as categorize

    folded = text.lower()
    area = RULE_AREA.get(rule)
    if area == "travel" and _EVENT_RE.search(folded) and not _TRAVEL_RE.search(folded):
        area = "agenda"  # Eventos y citas es área propia, separada de Viajes
    tags: list[str] = []
    if rule == "promotional":
        # Boletín o promoción: el área va por su tema; "promos" queda como etiqueta (y como triage).
        try:
            topic = categorize(sender, text.split("\n", 1)[0], [])
        except Exception:
            topic = None
        if topic in _TOPIC_AREAS and topic not in {"bills"}:
            area, tags = topic, ["promos"]
    if area is None:
        try:
            guess = categorize(sender, text.split("\n", 1)[0], [])
        except Exception:
            guess = None
        if guess in _TOPIC_AREAS or guess in {"security", "social", "promos"}:
            area = guess  # boletines van por su tema
        elif _MONEY_RE.search(folded):
            area = "money"
        else:
            area = "other" if confidence < 0.5 else None
    if area not in {"security", "bills"}:
        if _INSURANCE_RE.search(folded) and area != "insurance":
            tags.append("insurance")
        if _MONEY_RE.search(folded) and area != "money":
            tags.append("money")
    if area == "bills" and _INSURANCE_RE.search(folded):
        tags.append("insurance")
    return {"area": area, "tags": tags}
