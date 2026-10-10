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

# 13 áreas → esfera por defecto (catalogo-maestro.yaml; la app decide la esfera).
AREA_SPHERE: dict[str, str] = {
    "money": "personal", "bills": "hogar", "orders": "personal", "subscriptions": "personal",
    "work": "ocupacion", "home": "hogar", "health": "personal", "travel": "personal",
    "security": "personal", "government": "personal", "insurance": "hogar",
    "education": "personal", "agenda": "ocupacion",
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
    ("agenda", r"invitaci|invitation|calendar|calendario|reunion|meeting|evento|event|recordatorio|reminder"),
    ("work", r"proyecto|project|cliente|client|cotizaci|propuesta|contrato|nomina|payroll"),
    ("home", r"hogar|casa|renta|mantenimiento|condominio|familia|family"),
)
_PROMO_RE = re.compile(r"oferta|descuento|promo|sale|% off|newsletter|boletin|cupon|coupon|no te pierdas|ultimas horas")
_COMPILED = tuple((area, re.compile(pattern)) for area, pattern in _AREA_RULES)

CATEGORY_IDS = ("social", "promos", *AREA_SPHERE.keys(), "other")


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
    if "CATEGORY_PROMOTIONS" in label_set or _PROMO_RE.search(text):
        return "promos"
    return "other"


def clean_exclude(values: Iterable[str] | None) -> list[str]:
    allowed = set(CATEGORY_IDS)
    return sorted({str(v) for v in (values or []) if str(v) in allowed})


def skip_message(exclude: Iterable[str] | None, sender: str | None, subject: str | None, labels: Iterable[str] = ()) -> bool:
    excluded = set(exclude or ())
    return bool(excluded) and import_category(sender, subject, labels) in excluded


def gmail_query_exclusions(exclude: Iterable[str] | None) -> str:
    """Filtro de Gmail para no descargar lo excluido (búsqueda solo lectura)."""
    excluded = set(exclude or ())
    parts: list[str] = []
    if "social" in excluded:
        domains = " OR ".join(sorted(SOCIAL_PLATFORMS))
        parts.append(f"-category:social -from:({domains})")
    if "promos" in excluded:
        parts.append("-category:promotions")
    return " ".join(parts)


def summarize(headers: Iterable[tuple[str, str, list[str]]]) -> dict:
    """Cuenta una muestra de (remitente, asunto, etiquetas) por categoría, esfera y red."""
    categories: dict[str, int] = {key: 0 for key in CATEGORY_IDS}
    spheres = {"hogar": 0, "ocupacion": 0, "personal": 0}
    platforms: dict[str, int] = {}
    total = 0
    for sender, subject, labels in headers:
        total += 1
        category = import_category(sender, subject, labels)
        categories[category] += 1
        if category in AREA_SPHERE:
            spheres[AREA_SPHERE[category]] += 1
        platform = social_platform(sender)
        if platform:
            platforms[platform] = platforms.get(platform, 0) + 1
    return {"sampled": total, "categories": categories, "spheres": spheres, "social_platforms": platforms}
