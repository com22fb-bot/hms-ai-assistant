"""C1 · Reglas de seguridad, códigos y categorías protegidas (un solo módulo).

Lo usan: skip_message (exclusiones de la importación), el analizador del cerebro
v1 y, más adelante, el reconocedor de solo cabeceras del resumen previo.
Funciona con solo cabeceras (remitente, asunto, List-Id/List-Unsubscribe); si
hay cuerpo lo usa como señal adicional, nunca como requisito.
"""
from __future__ import annotations

import re
import unicodedata
from email.utils import parseaddr
from typing import Iterable, Mapping

PROTECTED_TYPES = ("security", "code", "bank", "government", "invoice", "health")


def fold(text: str | None) -> str:
    decomposed = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


SECURITY_RE = re.compile(
    r"(alerta de seguridad|security alert|aviso de seguridad|nuevo inicio de sesion|inicio de sesion (nuevo|sospechoso|inusual|desde)|"
    r"new sign-?in|sign-?in (attempt|alert|from)|suspicious (activity|sign|login)|unusual (activity|sign|login)|"
    r"actividad (inusual|sospechosa)|intento de (acceso|inicio)|nuevo dispositivo|new device|dispositivo no reconocido|"
    r"unrecognized device|contrasena (se ha )?(cambiad|actualizad|restablecid)|"
    # A1 (Etapa 1.2): cambio o restablecimiento de contraseña en cualquier redacción, también de redes sociales.
    r"(cambiaste|actualizaste|restableciste|se cambio|se actualizo|se restablecio) (tu |la |su )?contrasena|"
    r"contrasena\b[^.\n]{0,40}\b(se )?(cambio|actualizo|restablecio|modifico)|"
    r"password (has been |was )?(changed|updated|reset)|your password (was|has been)|cambio de contrasena|"
    r"new login detected|alguien (conoce|tiene|uso) tu contrasena|someone (knows|has|used) your password|"
    r"(bloqueamos|hemos bloqueado|se bloqueo) (el |tu )?acceso|acceso bloqueado|restablec\w* (tu |su )?contrasena|"
    r"password (changed|was changed|reset)|reset your password|two[- ]factor|2fa|autenticacion (en|de) dos|"
    r"protege tu cuenta|secure your account|cuenta (comprometida|bloqueada)|account (locked|compromised))",
)
# A2 (Etapa 1.2): alerta de seguridad que pide actuar ya → N1. "Si no fuiste tú, ..." es condicional (aviso).
SECURITY_ACTION_RE = re.compile(
    r"(alguien (conoce|tiene|uso) tu contrasena|someone (knows|has|used) your password|"
    r"(bloqueamos|hemos bloqueado|se bloqueo) (el |tu )?acceso|acceso bloqueado|cuenta (comprometida|bloqueada)|"
    r"account (locked|compromised)|(?<!si no fuiste tu, )(?<!si no fuiste tu )\bcambia (tu|la|su) contrasena|"
    r"change your password (now|immediately)|accion (inmediata|requerida)|immediate action)"
)
# A3 (Etapa 1.2): marcas que suplantan los fraudes. Se compara con el dominio del remitente.
PHISH_BRANDS = (
    "banamex", "citibanamex", "bbva", "santander", "banorte", "hsbc", "scotiabank", "inbursa", "banregio", "banco azteca",
    "nu", "paypal", "mercado pago", "mercadopago", "mercado libre", "mercadolibre", "amazon", "netflix", "apple", "icloud",
    "microsoft", "outlook", "hotmail", "google", "gmail", "facebook", "instagram", "whatsapp", "sat", "imss", "cfe",
    "telmex", "dhl", "fedex", "estafeta", "correos de mexico", "spotify", "uber", "didi", "liverpool", "coppel", "oxxo",
)
PHISH_ASK_RE = re.compile(
    r"(\bpaga\b|\bpague\b|\bpagar\b|realiza (un|el) pago|deposita|transfiere|verifica(r)? tu identidad|"
    r"confirma(r)? tus datos|actualiza(r)? tus datos|ingresa tus datos|tus datos bancarios|\bnip\b|\bcvv\b|"
    r"contrasena|clave de acceso|numero de tarjeta|verify your identity|confirm your (details|information)|update your (payment|billing))"
)
PHISH_URGENT_RE = re.compile(
    r"(enlace|link|haz clic|da clic|click|ingresa aqui|proximas? \d+ (horas|minutos)|\d+ horas|inmediat|urgente|"
    r"sera (suspendida|suspendido|bloqueada|cancelada)|suspend|hoy mismo|de lo contrario|within \d+ hours|immediately)"
)


def brand_mismatch(sender: str | None, subject: str | None, body: str | None = None) -> str | None:
    """Marca mencionada en asunto/cuerpo que no corresponde al dominio del remitente (o None)."""
    domain = re.sub(r"[^a-z0-9]", "", _domain(sender))
    if not domain:
        return None
    text = fold(f"{subject or ''}\n{(body or '')[:1600]}")
    for brand in PHISH_BRANDS:
        if re.search(r"\b" + re.escape(brand) + r"\b", text) and re.sub(r"[^a-z0-9]", "", brand) not in domain:
            if len(brand) <= 3 and not re.search(r"\b" + re.escape(brand) + r"\b", fold(subject or "")):
                continue  # siglas cortas (sat, cfe, nu) solo cuentan en el asunto
            return brand
    return None


def phishing_suspect(sender: str | None, subject: str | None, body: str | None = None) -> str | None:
    """A3: marca ajena al dominio + petición de pago/datos + clic o urgencia → marca suplantada; si no, None."""
    brand = brand_mismatch(sender, subject, body)
    if not brand:
        return None
    text = fold(f"{subject or ''}\n{(body or '')[:1600]}")
    if PHISH_ASK_RE.search(text) and PHISH_URGENT_RE.search(text):
        return brand
    return None


CODE_RE = re.compile(
    r"(codigo de (verificacion|seguridad|acceso|confirmacion)|verification code|security code|login code|"
    r"one[- ]time (pass(word|code)|code)|\botp\b|es tu codigo|is your .{0,30}code|clave dinamica|token de acceso|"
    r"codigo de un solo uso)"
)
_BANK_RE = re.compile(r"\b(banco|bank|bbva|banorte|santander|banamex|citibanamex|hsbc|scotiabank|inbursa|banregio|nu mexico|tarjeta de credito|credit card|estado de cuenta)\b")
_GOV_DOMAIN_RE = re.compile(r"(\.gob\.mx|\.gov(\.[a-z]{2})?|sat\.gob|imss|issste|infonavit|ine\.mx)$")
_GOV_RE = re.compile(r"\b(sat|imss|issste|infonavit|gobierno|government|tesoreria|predial|tenencia|impuesto|declaracion anual|buzon tributario|irs)\b")
_INVOICE_RE = re.compile(
    r"(factura|cfdi|recibo|invoice|\bbill\b|billing|estado de cuenta|statement|\bcargo\b|cobro|cobranza|adeudo|saldo pendiente|"
    r"amount due|payment due|pago pendiente|vence|vencimiento|aviso de pago|fecha limite de pago|telmex|\bcfe\b|mensualidad|colegiatura|cuota|\bpago\b|payment|receipt|abono)"
)
_HEALTH_RE = re.compile(r"(\bcita\b|appointment|clinica|clinic|hospital|laboratorio|\blab\b|receta|prescription|consulta medica|resultados de (tu|su) estudio|dr\.|dra\.)")


def _domain(sender: str | None) -> str:
    address = parseaddr(str(sender or ""))[1] or str(sender or "")
    return address.rsplit("@", 1)[-1].strip().lower().strip(">") if "@" in address else ""


def is_security_or_code(sender: str | None, subject: str | None, body: str | None = None) -> str | None:
    """'security' | 'code' | None. Se evalúa antes que cualquier exclusión."""
    text = fold(f"{subject or ''}\n{(body or '')[:1600]}")
    if CODE_RE.search(text):
        return "code"
    if SECURITY_RE.search(text):
        return "security"
    return None


def protected_type(
    sender: str | None,
    subject: str | None,
    body: str | None = None,
    headers: Mapping[str, str] | None = None,
    labels: Iterable[str] = (),
) -> str | None:
    """Tipo protegido (nunca se excluye por defecto) o None.

    Orden: seguridad/códigos → gobierno → banco → factura/pago → salud.
    """
    sec = is_security_or_code(sender, subject, body)
    if sec:
        return sec
    domain = _domain(sender)
    text = fold(f"{subject or ''}\n{(body or '')[:1600]}")
    sender_text = fold(f"{sender or ''}")
    if _GOV_DOMAIN_RE.search(domain) or _GOV_RE.search(text):
        return "government"
    try:
        from app.services.classification_catalog import identify_sender

        identity = identify_sender(sender) or {}
    except Exception:  # pragma: no cover - catálogo opcional
        identity = {}
    if identity.get("vertical") == "bank" or _BANK_RE.search(sender_text):
        # Un boletín bancario con List-Unsubscribe y sin términos de cobro no es protegido.
        if not (headers and headers.get("list-unsubscribe") and not _INVOICE_RE.search(text)):
            return "bank"
    if _INVOICE_RE.search(text):
        return "invoice"
    if _HEALTH_RE.search(text):
        return "health"
    return None
