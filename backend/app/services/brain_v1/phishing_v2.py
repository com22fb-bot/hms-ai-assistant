"""Detector de phishing y fraude para marcas DESCONOCIDAS (cerebro v1 + taxonomía v2; solo con BRAIN_V1_ENABLED).

``protected.phishing_suspect`` solo reconoce marcas conocidas. Este detector suma señales genéricas:
  1. dominio parecido (marca + sufijo de verificación/soporte, TLD doble, enlace a otro dominio);
  2. petición de contraseña, NIP, CVV o usuario por correo o enlace;
  3. cobro pequeño por enlace para "liberar" algo (aduana, paquete retenido);
  4. fraude de CEO (transferencia urgente/confidencial a una cuenta nueva);
  5. rendimientos demasiado buenos ("duplica tu dinero", "ganancias garantizadas");
  6. cripto/inversión con depósito; 7. premio no solicitado que pide tus datos.
Decide con una señal fuerte (2, 4, 5 o 6+depósito) o con dos señales cualesquiera. Nunca baja una alerta legítima:
las frases "no lo compartas", "desde la app/sitio oficial" anulan la señal 2.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_URL_RE = re.compile(r"https?://([a-z0-9.-]+)")
_LOOKALIKE_LABEL_RE = re.compile(
    r"[a-z0-9]+-(verifica\w*|verify\w*|seguridad|security|secure|soporte|support|login|validacion|validar|"
    r"alerta\w*|cuenta\w*|account\w*|mail|webmail|update|actualiza\w*|aduana|pago\w*)\b")
_DOUBLE_TLD_RE = re.compile(r"\.(co|com|net|org)\.(example|[a-z]{2,3})$")
_CRED_RE = re.compile(
    r"(confirma|ingresa|escribe|valida|proporciona|envia|enviar|actualiza|introduce|verifica|enter|confirm|provide|type)"
    r"[^.\n]{0,60}\b(contrasena|password|nip|\bpin\b|cvv|clave de acceso|usuario y contrasena|datos de (tu )?tarjeta)")
_CRED_ALT_RE = re.compile(r"(tu|your) (contrasena|password|nip|pin) actual")
_SAFE_RE = re.compile(r"(no (lo |la )?(compartas|compartir)|nunca (te )?(pediremos|solicitamos)|never ask|app oficial|sitio oficial)")
_FEE_RE = re.compile(r"(paga|pague|pagar|pay)\b[^.\n]{0,40}\$?\s?\d{1,4}(\.\d{2})?[^.\n]{0,60}(aduana|customs|liberar|retenid|envio|fee|tarifa)"
                     r"|(liberar|retenid)[^.\n]{0,60}(paga|pay)")
_CEO_RE = re.compile(r"(transferencia|wire|deposito)[^\n]{0,80}(nueva cuenta|cuenta nueva|esta cuenta|new account)")
_CEO_PRESSURE_RE = re.compile(r"(confidencial|no lo comentes|urgente|hoy mismo|\bhoy\b|discrec|asap)")
_TOO_GOOD_RE = re.compile(r"(duplica tu dinero|ganancias garantizadas|rendimientos? garantizad|guaranteed (returns|profit)|"
                          r"multiplica tu (dinero|inversion)|sin riesgo.{0,30}(ganancia|rendimiento))")
_CRYPTO_RE = re.compile(r"(cripto|crypto|bitcoin|\bbtc\b|usdt|ethereum|forex)")
_DEPOSIT_RE = re.compile(r"(deposita|invierte|transfiere|send)[^.\n]{0,40}(cuenta|wallet|\$|desde)")
_PRIZE_RE = re.compile(r"(ganaste|has sido seleccionad|eres el ganador|you (have )?won|felicidades.{0,30}(premio|iphone|ganaste))")
_DATA_ASK_RE = re.compile(r"(tus datos|datos personales|respondiendo con|reclama tu premio|claim your prize)")
_URGENT_LINK_RE = re.compile(r"(suspendid|bloquead|lleno|perder|expira)")


@dataclass
class PhishingVerdict:
    is_phishing: bool = False
    signals: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


def _lookalike(sender_domain: str, link_hosts: list[str]) -> bool:
    d = (sender_domain or "").lower()
    if d and (_LOOKALIKE_LABEL_RE.search(d) or _DOUBLE_TLD_RE.search(d)):
        return True
    return any(_LOOKALIKE_LABEL_RE.search(h) for h in link_hosts)


def detect(sender: str, text: str) -> PhishingVerdict:
    """``text`` plegado (minúsculas, sin acentos)."""
    sender = (sender or "").lower()
    domain = sender.rsplit("@", 1)[-1].strip(">") if "@" in sender else ""
    hosts = _URL_RE.findall(text)
    sig: list[str] = []
    tags: list[str] = []
    if _lookalike(domain, hosts):
        sig.append("dominio_parecido"); tags.append("Suplantación de identidad")
    elif hosts and domain and not any(h.endswith(domain.split(".", 1)[-1]) for h in hosts) and _URGENT_LINK_RE.search(text):
        sig.append("enlace_otro_dominio")
    safe = bool(_SAFE_RE.search(text))
    cred = bool(_CRED_RE.search(text) or _CRED_ALT_RE.search(text)) and not safe
    if cred:
        sig.append("pide_credenciales"); tags.append("Phishing sospechoso")
    fee = bool(_FEE_RE.search(text)) and bool(hosts)
    if fee:
        sig.append("cobro_por_enlace"); tags.append("Fraude financiero")
    ceo = bool(_CEO_RE.search(text) and _CEO_PRESSURE_RE.search(text))
    if ceo:
        sig.append("fraude_ceo"); tags.append("Cambio sospechoso de datos bancarios")
    too_good = bool(_TOO_GOOD_RE.search(text))
    if too_good:
        sig.append("rendimiento_irreal"); tags.append("Fraude financiero")
    crypto = bool(_CRYPTO_RE.search(text) or "crypto@" in sender or "cripto" in domain)
    deposit = bool(_DEPOSIT_RE.search(text))
    if crypto and (deposit or too_good):
        sig.append("cripto_deposito"); tags.append("Fraude financiero")
    prize = bool(_PRIZE_RE.search(text) and _DATA_ASK_RE.search(text))
    if prize:
        sig.append("premio_pide_datos"); tags.append("Suplantación de identidad")
    strong = cred or ceo or too_good or prize or (fee and "dominio_parecido" in sig) or ("cripto_deposito" in sig)
    return PhishingVerdict(is_phishing=bool(strong or len(sig) >= 2), signals=sig, tags=list(dict.fromkeys(tags)))
