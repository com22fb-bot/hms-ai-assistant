"""C2 · Fechas: vencimiento (due_at) y evento (event_at) separados.

- Se resuelven en America/Mexico_City tomando como ancla la fecha de recepción.
- Solo se toma una fecha si la oración trae una señal explícita (vence, fecha
  límite, a más tardar, cita, reunión...). Sin señal → None (nunca se inventa).
- Si hay dos fechas distintas para el mismo rol, o un formato dd/mm vs mm/dd
  indecidible → None + date_ambiguous=True.
- Cada fecha guarda su fragmento de evidencia.
"""
from __future__ import annotations

import calendar
import re
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from app.services.brain_v1.protected import fold

MX = ZoneInfo("America/Mexico_City")

MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
    "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "jun": 6, "jul": 7, "ago": 8, "sep": 9, "sept": 9,
    "oct": 10, "nov": 11, "dic": 12, "jan": 1, "apr": 4, "aug": 8, "dec": 12, "may": 5,
}
WEEKDAYS = {
    "lunes": 0, "martes": 1, "miercoles": 2, "jueves": 3, "viernes": 4, "sabado": 5, "domingo": 6,
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6,
}
NUMBERS = {"un": 1, "una": 1, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7,
           "diez": 10, "quince": 15, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "seven": 7, "ten": 10}

DUE_CUE = re.compile(
    r"(venc|fecha limite|limite de pago|a mas tardar|antes del?\b|pagar? (antes|hasta)|fecha de pago|paga antes|"
    r"\bdue\b|deadline|vence em|vencimento|echeance|date limite|a payer avant|no later than|\bby\b|plazo|tienes hasta|tiene hasta|hasta el|envi(a|e|es|ar|en|ame|anos)\b|mand(a|e|es|ar)\b|entreg|send|submit|\bpaga(r)?\b|pague)"
)
EVENT_CUE = re.compile(
    r"(\bcita\b|appointment|reunion|meeting|consulta|\bevento\b|\bevent\b|vuelo|flight|agendad|programad|scheduled|"
    r"webinar|entrevista|interview|llegue|arrive|itinerario|itinerary|reservacion|reservation|check-?in|"
    r"reprogramad|rescheduled|registro (esta )?confirmado|\bjunta\b|\bdeparts?\b|te esperamos|"
    r"entradas?|boletos?|tickets?|hospedaje|estancia|alojamiento|hotel|\bstay\b|lodging|concierto|concert|funcion|"
    # Post lote 4: reservas de restaurante o lugar ("tu mesa está reservada para el ...").
    r"\breserva\b|\breservad[ao]s?\b|\bmesa\b|salida|departure|"
    # L7reg1 (6): "se realizará el ...", fr/pt ("aura lieu", "confirmée pour le").
    r"se realizara|tendra lugar|aura lieu|confirmee pour|sera realizad|\bfestival\b)"
)
QUOTE_HEADER_RE = re.compile(r"(\b(escribio|wrote)\s*:|^\s*>|forwarded message|mensaje reenviado|mensaje original|original message)")
RENEWAL_CUE = re.compile(r"(renovar|renueva|renew|proximo cobro|proximo cargo|next (charge|billing))")
_MONTH_NAMES = "|".join(sorted(MONTHS, key=len, reverse=True))
_WD = "|".join(WEEKDAYS)
_NUM = r"(\d{1,2}|" + "|".join(NUMBERS) + r")"

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("iso", re.compile(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b")),
    ("slash", re.compile(r"\b(\d{1,2})[/.](\d{1,2})[/.](20\d{2}|\d{2})\b")),
    # A12 (Etapa 1.3): rango "del 12 al 15 de diciembre" → empieza el 12.
    ("es_range", re.compile(r"\bdel? (\d{1,2}) al (\d{1,2}) de (" + _MONTH_NAMES + r")\.?(?:,? (?:de|del)? ?(20\d{2}))?\b")),
    ("es_long", re.compile(r"\b(\d{1,2}) de (" + _MONTH_NAMES + r")\.?(?:,? (?:de|del)? ?(20\d{2}))?\b")),
    ("en_long", re.compile(r"\b(" + _MONTH_NAMES + r")\.? (\d{1,2})(?:st|nd|rd|th)?(?:,? (20\d{2}))?\b")),
    ("en_dmy", re.compile(r"\b(\d{1,2}) (" + _MONTH_NAMES + r")\.? (20\d{2})\b")),
    ("pasado", re.compile(r"\bpasado manana\b")),
    ("manana", re.compile(r"(?<!de la )\b(manana|tomorrow)\b(?! (por|en) la)")),
    ("hoy", re.compile(r"\b(hoy mismo|hoy|today)\b")),
    ("weekday", re.compile(r"\b(?:(el|este|esta|el proximo|proximo|next|this|on|el siguiente)\s+)?(" + _WD + r")\b")),
    ("in_days", re.compile(r"\b(?:en|dentro de|in|within)\s+" + _NUM + r"\s+(dias|dia|days|day|semanas|semana|weeks|week)\b")),
    ("eom", re.compile(r"\b(fin de mes|finales de mes|end of (the )?month|ultimo dia del mes)\b")),
]
TIME_RE = re.compile(r"\b(\d{1,2})(?::(\d{2}))\s*(am|pm|a\.m\.|p\.m\.|hrs|h)?\b|\b(\d{1,2})\s*(am|pm|a\.m\.|p\.m\.)\b")
# A9: "a las 9:00 de la noche/tarde" → pm; "de la mañana" → am.
PM_HINT_RE = re.compile(r"\b(de la (tarde|noche)|in the (afternoon|evening))\b")


@dataclass
class Found:
    role: str
    value: date
    evidence: str
    at: time | None = None


@dataclass
class DateResult:
    due_at: str | None = None
    due_evidence: str | None = None
    event_at: str | None = None
    event_evidence: str | None = None
    event_time_known: bool = False
    date_ambiguous: bool = False
    ambiguous_evidence: str | None = None
    candidates: list[dict[str, Any]] = field(default_factory=list)

    def as_metadata(self) -> dict[str, Any]:
        return {
            "due_at": self.due_at, "due_evidence": self.due_evidence,
            "event_at": self.event_at, "event_evidence": self.event_evidence,
            "event_time_known": self.event_time_known,
            "date_ambiguous": self.date_ambiguous, "ambiguous_evidence": self.ambiguous_evidence,
        }


def received_local(received_at: str | datetime | None) -> datetime:
    if isinstance(received_at, datetime):
        value = received_at
    else:
        try:
            value = datetime.fromisoformat(str(received_at).replace("Z", "+00:00"))
        except ValueError:
            value = datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(MX)


def _year_for(month: int, day: int, anchor: date) -> int:
    candidate = date(anchor.year, month, min(day, calendar.monthrange(anchor.year, month)[1]))
    if candidate < anchor - timedelta(days=60):
        return anchor.year + 1
    return anchor.year


def _safe(y: int, m: int, d: int) -> date | None:
    try:
        return date(y, m, d)
    except ValueError:
        return None


# A9 (Etapa 1.2): "martes 20 de octubre", "jueves, 29 de octubre de 2026": el día de la semana confirma la fecha
# explícita, no es otra fecha. Si no coincide con la fecha, es ambiguo.
WEEKDAY_WITH_DATE_RE = re.compile(r"\b(" + "|".join(WEEKDAYS) + r")\b,?\s+(?:el\s+)?(?=\d{1,2}(?: de |[/.-]| (?:" + "|".join(sorted(MONTHS, key=len, reverse=True)) + r")))")


# "hoy" se conserva: es el mismo día de recepción (política A14), no una inferencia.
_RELATIVE_KINDS = {"pasado", "manana", "weekday", "in_days", "eom"}


def _parse_in(sentence: str, anchor: date, english: bool, *, explicit_only: bool = False) -> list[tuple[date | str, int]]:
    """Fechas en la oración: (fecha | 'AMBIGUOUS', posición). explicit_only: sin fechas relativas (mañana, el viernes)."""
    out: list[tuple[date | str, int]] = []
    taken: list[tuple[int, int]] = []
    named_weekdays = [(m[1], m.start()) for m in WEEKDAY_WITH_DATE_RE.finditer(sentence)]
    if named_weekdays:
        sentence = WEEKDAY_WITH_DATE_RE.sub(lambda m: " " * len(m[0]), sentence)  # misma longitud: posiciones intactas

    def free(span: tuple[int, int]) -> bool:
        return all(span[1] <= a or span[0] >= b for a, b in taken)

    for kind, pattern in PATTERNS:
        if explicit_only and kind in _RELATIVE_KINDS:
            continue
        for m in pattern.finditer(sentence):
            if not free(m.span()):
                continue
            value: date | str | None = None
            if kind == "iso":
                value = _safe(int(m[1]), int(m[2]), int(m[3]))
            elif kind == "slash":
                a, b, y = int(m[1]), int(m[2]), int(m[3])
                y = y + 2000 if y < 100 else y
                if english and a <= 12 and b <= 12 and a != b:
                    value = "AMBIGUOUS"
                elif english and a <= 12:
                    value = _safe(y, a, b)
                else:
                    value = _safe(y, b, a)
            elif kind == "es_range":
                d, mo = int(m[1]), MONTHS[m[3]]
                y = int(m[4]) if m[4] else _year_for(mo, d, anchor)
                value = _safe(y, mo, d)
            elif kind == "es_long":
                d, mo = int(m[1]), MONTHS[m[2]]
                y = int(m[3]) if m[3] else _year_for(mo, d, anchor)
                value = _safe(y, mo, d)
            elif kind == "en_long":
                if m[1] == "may" and not english:
                    continue
                mo, d = MONTHS[m[1]], int(m[2])
                y = int(m[3]) if m[3] else _year_for(mo, d, anchor)
                value = _safe(y, mo, d)
            elif kind == "en_dmy":
                value = _safe(int(m[3]), MONTHS[m[2]], int(m[1]))
            elif kind == "pasado":
                value = anchor + timedelta(days=2)
            elif kind == "manana":
                value = anchor + timedelta(days=1)
            elif kind == "hoy":
                value = anchor
            elif kind == "weekday":
                target = WEEKDAYS[m[2]]
                delta = (target - anchor.weekday()) % 7
                value = anchor + timedelta(days=delta or 7)
            elif kind == "in_days":
                raw = m[1]
                n = int(raw) if raw.isdigit() else NUMBERS.get(raw, 0)
                unit = m[2]
                n = n * 7 if unit.startswith(("seman", "week")) else n
                value = anchor + timedelta(days=n) if n else None
            elif kind == "eom":
                value = date(anchor.year, anchor.month, calendar.monthrange(anchor.year, anchor.month)[1])
            if value is None:
                continue
            taken.append(m.span())
            out.append((value, m.start()))
    out.sort(key=lambda item: item[1])
    for name, pos in named_weekdays:
        nxt = next((i for i, (_, at) in enumerate(out) if at >= pos), None)
        if nxt is not None and isinstance(out[nxt][0], date) and out[nxt][0].weekday() != WEEKDAYS[name]:
            out[nxt] = ("AMBIGUOUS", out[nxt][1])
    return out


def _time_in(sentence: str) -> time | None:
    m = TIME_RE.search(sentence)
    if not m:
        return None
    if m[1] is not None:
        h, mi, suffix = int(m[1]), int(m[2] or 0), (m[3] or "")
    else:
        h, mi, suffix = int(m[4]), 0, m[5]
    if suffix.startswith("p") and h < 12:
        h += 12
    if suffix.startswith("a") and h == 12:
        h = 0
    if not suffix and PM_HINT_RE.search(sentence) and h < 12:
        h += 12
    if h > 23 or mi > 59:
        return None
    return time(h, mi)


def _is_today_only(sentence: str, item: tuple[Any, int]) -> bool:
    return bool(re.match(r"(hoy mismo|hoy|today)\b", sentence[item[1]:item[1] + 9]))


_SPLIT = re.compile(r"(?<=[.!?;\n])\s+|\n+")


def extract_dates(subject: str | None, body: str | None, received_at: Any, *, kind: str | None = None) -> DateResult:
    local = received_local(received_at)
    anchor = local.date()
    raw = f"{subject or ''}.\n{body or ''}"[:6000]
    english = bool(re.search(r"\b(the|your|please|due|appointment|invoice|payment)\b", raw.lower()))
    found: list[Found] = []
    ambiguous: str | None = None
    # A9/A8: en citas, eventos y esperas, la señal puede venir en el asunto ("Webinar ...", "Tu itinerario").
    subject_event = kind in {"appointment", "appointment_cancel", "event", "booking"} and bool(EVENT_CUE.search(fold(subject or "")))
    for sentence_raw in _SPLIT.split(raw):
        sentence = fold(sentence_raw).strip()
        if not sentence:
            continue
        has_due = bool(DUE_CUE.search(sentence))
        has_event = bool(EVENT_CUE.search(sentence)) or subject_event
        if kind == "waiting":
            has_due, has_event = True, False
        if kind == "renewal":
            # Post lote 4: la fecha de una renovación próxima es la fecha del cobro (vencimiento), solo con señal explícita.
            has_due, has_event = bool(RENEWAL_CUE.search(sentence)), False
        if not (has_due or has_event):
            continue
        if kind in {"appointment", "appointment_cancel", "event", "booking"} and has_event:
            role = "event"
        elif has_due:
            role = "due"
        else:
            role = "event"
        # Fix event_at: un evento solo toma fecha escrita; "mañana", "el viernes" o "en 3 días" no crean event_at.
        # Las cabeceras de citas reenviadas ("El 3 oct 2026, Ana escribió:") no son la fecha del evento.
        if role == "event" and QUOTE_HEADER_RE.search(sentence):
            continue
        dates = _parse_in(sentence, anchor, english, explicit_only=(role == "event"))
        if role == "due":
            # L7reg1 (6): "hoy" como vencimiento sería copiar received_at en due_at → no se usa.
            dates = [d for d in dates if not _is_today_only(sentence, d)]
        if not dates:
            continue
        evidence = sentence_raw.strip()[:240]
        distinct = {d for d, _ in dates}
        if (kind == "booking" and len(distinct) == 2 and "AMBIGUOUS" not in distinct
                and re.search(r"\bdel?\b[^.]{0,40}\bal?\b", sentence) and role == "event"):
            # Post lote 4 (4): "del 2026-12-15 al 2026-12-18" (llegada y salida) → empieza en la primera fecha.
            distinct = {min(distinct)}  # type: ignore[type-var]
            dates = [(min(d for d, _ in dates), dates[0][1])]  # type: ignore[type-var]
        if "AMBIGUOUS" in distinct or len(distinct) > 1:
            ambiguous = evidence
            continue
        value = dates[0][0]
        assert isinstance(value, date)
        found.append(Found(role, value, evidence, _time_in(sentence) if role == "event" else None))

    result = DateResult(candidates=[{"role": f.role, "date": f.value.isoformat(), "evidence": f.evidence} for f in found])
    for role in ("due", "event"):
        items = [f for f in found if f.role == role]
        values = {f.value for f in items}
        if role == "event" and kind == "booking" and len(values) > 1:
            # A12: una reservación trae llegada y salida; el compromiso empieza en la primera fecha.
            first = min(values)
            items = [f for f in items if f.value == first]
            values = {first}
        if len(values) > 1:
            result.date_ambiguous = True
            result.ambiguous_evidence = items[-1].evidence
            continue
        if not items:
            continue
        f = items[0]
        if role == "due":
            result.due_at = datetime.combine(f.value, time(23, 59), MX).isoformat()
            result.due_evidence = f.evidence
        else:
            at = next((i.at for i in items if i.at), None)
            result.event_at = datetime.combine(f.value, at or time(0, 0), MX).isoformat()
            result.event_time_known = at is not None
            result.event_evidence = f.evidence
    if ambiguous and not (result.due_at or result.event_at):
        result.date_ambiguous = True
        result.ambiguous_evidence = ambiguous
    return result
