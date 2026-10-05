"""Remitentes de servicios, gobierno, AFORE, cobranza y cobro de software.

Cada directorio dice QUÉ es el remitente. Si un correo crea un caso lo
decide ``case_policy`` por el contenido (aviso de cobro, adeudo…), nunca
sólo por el remitente.
"""

from __future__ import annotations


def _add(
    directory: dict[str, dict[str, str]],
    vertical: str,
    name: str,
    region: str,
    country: str,
    *domains: str,
) -> None:
    meta = {"name": name, "region": region, "country": country, "vertical": vertical}
    for domain in domains:
        directory[domain.lower().strip()] = meta


UTILITIES: dict[str, dict[str, str]] = {}
_add(UTILITIES, "utility", "CFE", "MX", "MX", "cfe.mx", "cfe.gob.mx")
_add(UTILITIES, "utility", "Telcel", "MX", "MX", "telcel.com", "mail.telcel.com")
_add(UTILITIES, "utility", "Totalplay", "MX", "MX", "totalplay.com.mx")
_add(UTILITIES, "utility", "Telmex", "MX", "MX", "telmex.com", "telmex.com.mx")
_add(UTILITIES, "utility", "izzi", "MX", "MX", "izzi.mx", "izzi.com.mx")
_add(UTILITIES, "utility", "Megacable", "MX", "MX", "megacable.com.mx")
_add(UTILITIES, "utility", "AT&T México", "MX", "MX", "att.com.mx")
_add(UTILITIES, "utility", "Naturgy México", "MX", "MX", "naturgy.com.mx")
_add(UTILITIES, "utility", "ECOGAS", "MX", "MX", "sempraglobal.com.mx", "ecogas.com.mx")
_add(UTILITIES, "utility", "SACMEX", "MX", "MX", "sacmex.cdmx.gob.mx")

GOVERNMENT: dict[str, dict[str, str]] = {}
_add(GOVERNMENT, "government", "ISSSTE", "MX", "MX", "issste.gob.mx")
_add(GOVERNMENT, "government", "IMSS", "MX", "MX", "imss.gob.mx")
_add(GOVERNMENT, "government", "SAT", "MX", "MX", "sat.gob.mx")
_add(GOVERNMENT, "government", "Infonavit", "MX", "MX", "infonavit.org.mx")
_add(GOVERNMENT, "government", "FOVISSSTE", "MX", "MX", "fovissste.gob.mx")
_add(GOVERNMENT, "government", "DIF", "MX", "MX", "dif.gob.mx")
_add(GOVERNMENT, "government", "IRS", "US", "US", "irs.gov")

PENSIONS: dict[str, dict[str, str]] = {}
_add(PENSIONS, "pension", "Profuturo", "MX", "MX", "profuturo.mx", "profuturo.com.mx")
_add(PENSIONS, "pension", "Afore XXI Banorte", "MX", "MX", "xxi-banorte.com", "aforexxi.com")
_add(PENSIONS, "pension", "Afore Coppel", "MX", "MX", "aforecoppel.com")
_add(PENSIONS, "pension", "Afore Sura", "MX", "MX", "suramexico.com")
_add(PENSIONS, "pension", "CONSAR", "MX", "MX", "consar.gob.mx")

# Despachos de cobranza externa: cobran en nombre de un banco. Nunca se
# paga sin verificar con el banco (ver case_policy: precaución).
DEBT_COLLECTION: dict[str, dict[str, str]] = {}
_add(DEBT_COLLECTION, "debt_collection", "Conjurnet (despacho de cobranza)", "MX", "MX", "conjurnet.com.mx")
_add(DEBT_COLLECTION, "debt_collection", "Milla Asistencia (despacho de cobranza)", "MX", "MX", "milla-asistencia.mx")
_add(DEBT_COLLECTION, "debt_collection", "Cartera jurídica (despacho de cobranza)", "MX", "MX", "comunicacioncartjur.mx")

PAYMENT_PROCESSORS: dict[str, dict[str, str]] = {}
_add(PAYMENT_PROCESSORS, "payment_processor", "Cleverbridge", "GLOBAL", "US", "cleverbridge.com")
_add(PAYMENT_PROCESSORS, "payment_processor", "Paddle", "GLOBAL", "GB", "paddle.com")
_add(PAYMENT_PROCESSORS, "payment_processor", "FastSpring", "GLOBAL", "US", "fastspring.com")
_add(PAYMENT_PROCESSORS, "payment_processor", "2Checkout", "GLOBAL", "US", "2checkout.com")

COLLECTION_LOCAL_PARTS = ("cobranza", "cobranzas", "recuperacion", "extrajudicial", "despacho")


def is_collection_local_part(local: str) -> bool:
    compact = (local or "").lower()
    return any(compact.startswith(marker) for marker in COLLECTION_LOCAL_PARTS)
