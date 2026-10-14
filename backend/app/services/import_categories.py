"""Categorías de la importación personalizada (onboarding «historial listo»).

Clasificación ligera por remitente y asunto, solo para la vista previa y para
saltar categorías que el usuario excluyó. No sustituye al clasificador de casos.
Solo lectura: nunca modifica nada en el proveedor.
"""

from __future__ import annotations

import re
import unicodedata
from email.utils import parseaddr
from typing import Iterable

# Redes sociales globales detectadas por dominio del remitente.
SOCIAL_PLATFORMS: dict[str, str] = {
    "youtube.com": "YouTube", "instagram.com": "Instagram", "facebookmail.com": "Facebook",
    "facebook.com": "Facebook", "fb.com": "Facebook", "tiktok.com": "TikTok", "tiktokv.com": "TikTok",
    "linkedin.com": "LinkedIn", "x.com": "X/Twitter", "twitter.com": "X/Twitter",
    "snapchat.com": "Snapchat", "telegram.org": "Telegram", "whatsapp.com": "WhatsApp",
    "pinterest.com": "Pinterest", "redditmail.com": "Reddit", "reddit.com": "Reddit",
    "discord.com": "Discord", "discordapp.com": "Discord", "threads.net": "Threads",
    "wechat.com": "WeChat", "vk.com": "VK", "twitch.tv": "Twitch", "tumblr.com": "Tumblr",
    "quora.com": "Quora", "medium.com": "Medium", "bsky.app": "Bluesky", "mastodon.social": "Mastodon",
    "line.me": "LINE", "kakaocorp.com": "KakaoTalk", "weibo.com": "Weibo", "flickr.com": "Flickr",
    "nextdoor.com": "Nextdoor", "meetup.com": "Meetup", "strava.com": "Strava",
}

# Catálogo vigente de Donexto: 16 áreas (frontend/lib/nucleo/lifeAreas.ts · LIFE_AREA_IDS).
# 13 áreas de vida con esfera + 3 grupos sin esfera: social, promos, other.
# Cada mensaje cae en exactamente UNA categoría, así que los totales no se duplican.
AREA_SPHERE: dict[str, str] = {
    "money": "personal", "bills": "hogar", "orders": "personal", "subscriptions": "personal",
    "work": "ocupacion", "home": "hogar", "health": "personal", "travel": "personal",
    "security": "personal", "government": "personal", "insurance": "hogar",
    "education": "personal", "events": "ocupacion",
}

_AREA_RULES: tuple[tuple[str, str], ...] = (
    ("security", r"alerta de seguridad|security alert|contrasena|password|inicio de sesion|sign.?in|verificaci|verification code|codigo de"),
    ("bills", r"factura|recibo|invoice|cfdi|estado de cuenta|statement|cfe|telmex|izzi|totalplay|agua|predial"),
    ("money", r"pago|payment|cargo|transferencia|deposito|spei|banco|bank|tarjeta|card|paypal|mercado pago|reembolso|refund"),
    ("orders", r"pedido|order|envio|shipped|entrega|delivery|paquete|package|amazon|mercado libre|rastreo"),
    ("subscriptions", r"suscripci|subscription|renovaci|renewal|membresia|membership|netflix|spotify|disney|gym|gimnasio"),
    ("travel", r"vuelo|flight|reserva|booking|hotel|airbnb|aeromexico|volaris|viva ?aerobus|itinerario|check.?in"),
    ("health", r"cita medica|consulta|doctor|hospital|farmacia|laboratorio|salud|health|receta"),
    ("insurance", r"seguro|poliza|insurance|policy|gnp|axa|aseguradora"),
    ("government", r"\bsat\b|imss|issste|infonavit|gobierno|government|tramite|impuesto|tax|curp|rfc"),
    ("education", r"escuela|school|colegiatura|universidad|university|curso|course|clase"),
    ("events", r"invitaci|invitation|calendar|calendario|reunion|meeting|evento|event|recordatorio|reminder"),
    ("work", r"proyecto|project|cliente|client|cotizaci|propuesta|contrato|nomina|payroll"),
    ("home", r"hogar|casa|renta|mantenimiento|condominio|familia|family"),
)
_PROMO_RE = re.compile(r"oferta|descuento|promo|sale|% off|newsletter|boletin|cupon|coupon|no te pierdas|ultimas horas")
_COMPILED = tuple((area, re.compile(pattern)) for area, pattern in _AREA_RULES)

CATEGORY_IDS = ("social", "promos", *AREA_SPHERE.keys(), "other")
# Id antiguo de la vista previa → id del catálogo vigente.
_ALIASES = {"agenda": "events"}

# ── Taxonomía v2 (aprobada 13-oct-2026, docs/TAXONOMIA_V2.md) ─────────────────
# Solo vista previa e importación personalizada (cabeceras). No depende de
# BRAIN_V1_ENABLED y no cambia import_category (lo usa brain_v1).
# 3 mundos · 7 áreas. Seguridad es alerta transversal, no área. "Por revisar"
# es un estado. No existe "Otros".
V2_AREAS: tuple[tuple[str, str, str], ...] = (
    ("trabajo", "Trabajo y negocios", "ocupacion"),
    ("hogar", "Hogar y familia", "hogar"),
    ("dinero", "Dinero y facturas", "hogar"),
    ("compras", "Compras y suscripciones", "hogar"),
    ("salud", "Salud y seguros", "personal"),
    ("viajes", "Viajes y eventos", "personal"),
    ("promociones", "Promociones y social", "personal"),
)
V2_AREA_IDS = tuple(a for a, _, _ in V2_AREAS)
V2_AREA_WORLD = {a: w for a, _, w in V2_AREAS}
WORLD_IDS = ("ocupacion", "hogar", "personal")
REVIEW_ID = "revisar"
LEGACY_TO_V2: dict[str, str] = {
    "work": "trabajo",
    "home": "hogar", "education": "hogar",
    "money": "dinero", "bills": "dinero",
    # ASTRA: Gobierno/trámites no es un área v2; va a Por revisar (sigue protegido como "gobierno").
    "government": REVIEW_ID,
    "orders": "compras", "subscriptions": "compras",
    "health": "salud", "insurance": "salud",
    "travel": "viajes", "events": "viajes",
    "promos": "promociones", "social": "promociones",
    "other": REVIEW_ID,
}
# Categorías protegidas: se descargan aunque su área esté desmarcada, salvo que
# el usuario las apague (exclude contiene "proteger:<id>").
PROTECTED_IDS = ("seguridad", "bancos", "gobierno", "facturas", "salud")
PROTECTED_PREFIX = "proteger:"
_LEGACY_PROTECTED = {"money": "bancos", "government": "gobierno", "bills": "facturas", "health": "salud"}
_SECURITY_RE = dict(_COMPILED)["security"]
V2_EXCLUDE_IDS = (*V2_AREA_IDS, REVIEW_ID, *(PROTECTED_PREFIX + p for p in PROTECTED_IDS))


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def sender_domain(sender: str | None) -> str:
    address = parseaddr(str(sender or ""))[1] or str(sender or "")
    return address.rsplit("@", 1)[-1].strip().lower().strip(">") if "@" in address else ""


def social_platform(sender: str | None) -> str | None:
    domain = sender_domain(sender)
    for known, name in SOCIAL_PLATFORMS.items():
        if domain == known or domain.endswith("." + known):
            return name
    return None


def import_category(sender: str | None, subject: str | None, labels: Iterable[str] = ()) -> str:
    """social | promos | <área> | other."""
    if social_platform(sender):
        return "social"
    label_set = {str(label).upper() for label in labels}
    if "CATEGORY_SOCIAL" in label_set:
        return "social"
    text = _fold(f"{subject or ''} {sender or ''}")
    for area, pattern in _COMPILED:
        if pattern.search(text):
            return area
    if "CATEGORY_PROMOTIONS" in label_set or "HAS_LIST_HEADERS" in label_set or _PROMO_RE.search(text):
        return "promos"
    return "other"


def clean_exclude(values: Iterable[str] | None) -> list[str]:
    allowed = set(CATEGORY_IDS) | set(V2_EXCLUDE_IDS)
    mapped = (_ALIASES.get(str(v), str(v)) for v in (values or []))
    return sorted({v for v in mapped if v in allowed})


def is_security(sender: str | None, subject: str | None) -> bool:
    return bool(_SECURITY_RE.search(_fold(f"{subject or ''} {sender or ''}")))


def v2_area(sender: str | None, subject: str | None, labels: Iterable[str] = ()) -> str:
    """Área v2 (una de V2_AREA_IDS) o "revisar". Seguridad nunca es área."""
    legacy = import_category(sender, subject, labels)
    if legacy == "security":
        text = _fold(f"{subject or ''} {sender or ''}")
        legacy = next((a for a, pat in _COMPILED if a != "security" and pat.search(text)), "other")
    return LEGACY_TO_V2.get(legacy, REVIEW_ID)


def protected_class(sender: str | None, subject: str | None, labels: Iterable[str] = ()) -> str | None:
    if is_security(sender, subject):
        return "seguridad"
    return _LEGACY_PROTECTED.get(import_category(sender, subject, labels))


def skip_message(exclude: Iterable[str] | None, sender: str | None, subject: str | None, labels: Iterable[str] = ()) -> bool:
    excluded = set(exclude or ())
    if not excluded:
        return False
    from app.services.brain_v1 import brain_v1_enabled

    if brain_v1_enabled():
        from app.services.brain_v1.protected import is_security_or_code

        # C1: seguridad y códigos nunca se saltan, aunque se excluya "social".
        if is_security_or_code(sender, subject):
            return False
        from app.services.brain_v1.protected import brand_mismatch

        # A15 (Etapa 1.3): un posible phishing nunca se excluye ni se oculta; solo puede ir a revisión.
        if brand_mismatch(sender, subject):
            return False
    if excluded & set(V2_EXCLUDE_IDS):
        # Elección v2 (pantalla nueva): protegidas encendidas nunca se saltan.
        protected = protected_class(sender, subject, labels)
        if protected and PROTECTED_PREFIX + protected not in excluded:
            return False
        if v2_area(sender, subject, labels) in excluded:
            return True
    # Ids heredados (importaciones guardadas antes de v2): comportamiento idéntico.
    return import_category(sender, subject, labels) in excluded


def gmail_query_exclusions(exclude: Iterable[str] | None) -> str:
    """Filtro de Gmail para no descargar lo excluido (búsqueda solo lectura)."""
    excluded = set(exclude or ())
    if "promociones" in excluded and all(PROTECTED_PREFIX + p in excluded for p in PROTECTED_IDS):
        excluded |= {"social", "promos"}
    parts: list[str] = []
    if "social" in excluded:
        domains = " OR ".join(sorted(SOCIAL_PLATFORMS))
        parts.append(f"-category:social -from:({domains})")
    if "promos" in excluded:
        parts.append("-category:promotions")
    return " ".join(parts)


def _sender_name(sender: str) -> str:
    name, address = parseaddr(str(sender or ""))
    name = (name or "").strip().strip('"')
    return name or address or str(sender or "")


# Un remitente solo aparece como ejemplo si envió al menos este número de
# correos (remitentes masivos u organizaciones, no personas sueltas).
EXAMPLE_MIN_MESSAGES = 3


def summarize(headers: Iterable[tuple[str, str, list[str]]], max_examples: int = 3) -> dict:
    """Cuenta una muestra de (remitente, asunto, etiquetas) por categoría, esfera y red."""
    categories: dict[str, int] = {key: 0 for key in CATEGORY_IDS}
    spheres = {"hogar": 0, "ocupacion": 0, "personal": 0}
    platforms: dict[str, int] = {}
    senders: dict[str, dict[str, int]] = {key: {} for key in CATEGORY_IDS}
    areas: dict[str, int] = {a: 0 for a in V2_AREA_IDS}
    worlds = {w: 0 for w in WORLD_IDS}
    areas_review = [0]
    security = 0
    protected: dict[str, int] = {p: 0 for p in PROTECTED_IDS}
    total = 0
    for sender, subject, labels in headers:
        total += 1
        category = import_category(sender, subject, labels)
        categories[category] += 1
        name = _sender_name(sender)
        if name:
            senders[category][name] = senders[category].get(name, 0) + 1
        if category in AREA_SPHERE:
            spheres[AREA_SPHERE[category]] += 1
        area = v2_area(sender, subject, labels)
        if area == REVIEW_ID:
            areas_review[0] += 1
        else:
            areas[area] += 1
            worlds[V2_AREA_WORLD[area]] += 1
        if is_security(sender, subject):
            security += 1
        prot = protected_class(sender, subject, labels)
        if prot:
            protected[prot] += 1
        platform = social_platform(sender)
        if platform:
            platforms[platform] = platforms.get(platform, 0) + 1
    examples = {
        key: [n for n, c in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])) if c >= EXAMPLE_MIN_MESSAGES][:max_examples]
        for key, counts in senders.items() if counts
    }
    examples = {k: v for k, v in examples.items() if v}
    for area in V2_AREA_IDS:
        merged: dict[str, int] = {}
        for legacy, target in LEGACY_TO_V2.items():
            if target == area:
                for n, c in senders.get(legacy, {}).items():
                    merged[n] = merged.get(n, 0) + c
        names = [n for n, c in sorted(merged.items(), key=lambda kv: (-kv[1], kv[0])) if c >= EXAMPLE_MIN_MESSAGES][:max_examples]
        if names:
            examples[area] = names
    return {
        "sampled": total, "categories": categories, "spheres": worlds,
        "worlds": worlds, "areas": areas, "review": areas_review[0],
        "security": security, "protected": protected,
        "social_platforms": platforms, "examples": examples, "taxonomy": "v2",
    }
