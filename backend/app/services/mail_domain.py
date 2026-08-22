"""Verificación de dominio de correo en el alta/login de Donexto.

Un dominio con @ y un punto no basta: hay que distinguir typo
(hotmil.com), dominio inexistente, proveedor activo, proveedor en
revisión (Gmail/iCloud) y dominio real aún no integrado.
"""

from __future__ import annotations

import re
import socket
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass
from typing import Callable

from app.services.microsoft_domains import MICROSOFT_MAIL_DOMAINS
from app.services.yahoo_domains import YAHOO_MAIL_DOMAINS

GMAIL_MAIL_DOMAINS = ("gmail.com", "googlemail.com")
APPLE_MAIL_DOMAINS = ("icloud.com", "me.com", "mac.com")

ACTIVE_OPTIONS_TEXT = "Yahoo y Outlook/Hotmail"
PENDING_OPTIONS_TEXT = "Gmail e iCloud"

_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", re.I)

# Errores frecuentes de tipeo → dominio canónico.
COMMON_TYPOS: dict[str, str] = {
    "hotmil.com": "hotmail.com",
    "hotmial.com": "hotmail.com",
    "htmail.com": "hotmail.com",
    "hotmal.com": "hotmail.com",
    "hotmail.co": "hotmail.com",
    "hotmail.con": "hotmail.com",
    "hotmail.cox": "hotmail.com",
    "hotmail.cm": "hotmail.com",
    "hitmail.com": "hotmail.com",
    "gmal.com": "gmail.com",
    "gmial.com": "gmail.com",
    "gmaill.com": "gmail.com",
    "gmail.con": "gmail.com",
    "gmail.cox": "gmail.com",
    "gmail.cm": "gmail.com",
    "googlemail.con": "googlemail.com",
    "yaho.com": "yahoo.com",
    "yahooo.com": "yahoo.com",
    "yahoo.con": "yahoo.com",
    "yahoo.cox": "yahoo.com",
    "yahoo.cm": "yahoo.com",
    "yaho.com.mx": "yahoo.com.mx",
    "outlok.com": "outlook.com",
    "outlook.con": "outlook.com",
    "outlook.cox": "outlook.com",
    "outlook.cm": "outlook.com",
    "iclod.com": "icloud.com",
    "icoud.com": "icloud.com",
    "icloud.con": "icloud.com",
}


def _roots_for(*groups: tuple[str, ...]) -> tuple[str, ...]:
    seen: list[str] = []
    for group in groups:
        for root in group:
            if root not in seen:
                seen.append(root)
    return tuple(seen)


KNOWN_ACTIVE_DOMAINS = _roots_for(YAHOO_MAIL_DOMAINS, MICROSOFT_MAIL_DOMAINS)
KNOWN_PENDING_DOMAINS = _roots_for(GMAIL_MAIL_DOMAINS, APPLE_MAIL_DOMAINS)
KNOWN_MAIL_DOMAINS = _roots_for(KNOWN_ACTIVE_DOMAINS, KNOWN_PENDING_DOMAINS)


def email_domain(email: str) -> str:
    at = (email or "").strip().lower().rfind("@")
    if at < 0:
        return ""
    return (email or "").strip().lower()[at + 1 :].strip(".")


def email_local_part(email: str) -> str:
    at = (email or "").strip().lower().rfind("@")
    if at <= 0:
        return ""
    return (email or "").strip().lower()[:at]


def _matches(domain: str, roots: tuple[str, ...]) -> bool:
    return any(domain == root or domain.endswith("." + root) for root in roots)


def provider_for_domain(domain: str) -> str:
    if not domain:
        return "other"
    if _matches(domain, GMAIL_MAIL_DOMAINS):
        return "gmail"
    if _matches(domain, YAHOO_MAIL_DOMAINS):
        return "yahoo"
    if _matches(domain, MICROSOFT_MAIL_DOMAINS):
        return "hotmail"
    if _matches(domain, APPLE_MAIL_DOMAINS):
        return "apple"
    return "other"


def is_plausible_hostname(domain: str) -> bool:
    if not domain or "." not in domain or len(domain) > 253:
        return False
    labels = domain.split(".")
    if any(not label or not _LABEL.match(label) for label in labels):
        return False
    return all(len(label) <= 63 for label in labels)


def edit_distance(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)
    previous = list(range(len(right) + 1))
    for i, char_l in enumerate(left, start=1):
        current = [i]
        for j, char_r in enumerate(right, start=1):
            insert = current[j - 1] + 1
            delete = previous[j] + 1
            replace = previous[j - 1] + (char_l != char_r)
            current.append(min(insert, delete, replace))
        previous = current
    return previous[-1]


def suggest_known_domain(domain: str) -> str | None:
    """Si parece un typo de un proveedor conocido, devuelve el dominio correcto."""
    clean = (domain or "").strip().lower().strip(".")
    if not clean or _matches(clean, KNOWN_MAIL_DOMAINS):
        return None
    mapped = COMMON_TYPOS.get(clean)
    if mapped:
        return mapped

    # hotmail.cox / hotmailer.cox: el TLD no es un servicio; se compara el nombre.
    name = clean
    if "." in clean:
        name, _, tld = clean.rpartition(".")
        if tld in {"cox", "con", "cm", "comm", "cpm"} and name:
            candidate = f"{name}.com"
            if _matches(candidate, KNOWN_MAIL_DOMAINS):
                return candidate

    best: str | None = None
    best_distance = 99
    for candidate in KNOWN_MAIL_DOMAINS:
        cand_name = candidate.split(".")[0]
        distance = min(
            edit_distance(clean, candidate),
            edit_distance(name, cand_name),
        )
        if distance < best_distance:
            best_distance = distance
            best = candidate
        elif distance == best_distance and best:
            prefer_com = candidate.endswith(".com") and not best.endswith(".com")
            shorter = len(candidate) < len(best)
            if prefer_com or (shorter and candidate.endswith(".com") == best.endswith(".com")):
                best = candidate

    if best is None:
        return None
    if best_distance <= 2 and len(name) >= 5:
        return best
    return None


def _lookup_host(domain: str) -> bool:
    try:
        return bool(socket.getaddrinfo(domain, None))
    except OSError:
        return False


def domain_has_mail_records(
    domain: str,
    timeout_seconds: float = 2.0,
) -> bool:
    """True si el dominio resuelve (A/AAAA). Sin registros → no está activo."""
    if not is_plausible_hostname(domain):
        return False
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_lookup_host, domain)
        try:
            return bool(future.result(timeout=timeout_seconds))
        except (FutureTimeout, OSError):
            return False


ACTIVE_OPTIONS_MESSAGE = (
    f"Opciones activas: {ACTIVE_OPTIONS_TEXT}. "
    f"{PENDING_OPTIONS_TEXT}: la solicitud de acceso está en revisión."
)


def message_for_typo(suggested_domain: str) -> str:
    return (
        "Ese dominio no coincide con un correo activo. "
        f"¿Quisiste decir {suggested_domain}? {ACTIVE_OPTIONS_MESSAGE}"
    )


def message_for_missing() -> str:
    return (
        "Ese dominio no está activo: no existe como correo. "
        f"{ACTIVE_OPTIONS_MESSAGE}"
    )


def message_for_pending(provider: str) -> str:
    label = "Gmail" if provider == "gmail" else "iCloud"
    other = "iCloud" if provider == "gmail" else "Gmail"
    return (
        f"{label}: la solicitud de acceso está en revisión. "
        f"Todavía no podemos completar el alta con ese correo. "
        f"Opciones activas: {ACTIVE_OPTIONS_TEXT}. "
        f"{other} también está en revisión."
    )


def message_for_unsupported() -> str:
    return (
        "Ese dominio existe, pero Donexto aún no lo tiene integrado. "
        "Ya avisamos a soporte para valorar el trámite. "
        f"Mientras tanto {ACTIVE_OPTIONS_MESSAGE}"
    )


@dataclass(frozen=True)
class DomainVerdict:
    email: str
    domain: str
    provider: str
    status: str
    suggested_email: str | None
    message: str

    @property
    def next_when_unknown(self) -> str:
        if self.status in {"typo", "missing"}:
            return "fix_domain"
        if self.status == "pending_review":
            return "pending_review"
        if self.status == "unsupported":
            return "unsupported"
        return "signup"


ProbeFn = Callable[[str], bool]


def classify_mail_domain(
    email: str,
    *,
    probe: ProbeFn | None = None,
) -> DomainVerdict:
    clean = (email or "").strip().lower()
    domain = email_domain(clean)
    local = email_local_part(clean)
    provider = provider_for_domain(domain)
    probe_fn = probe or domain_has_mail_records

    if not domain or not local or not is_plausible_hostname(domain):
        return DomainVerdict(
            email=clean,
            domain=domain,
            provider="other",
            status="missing",
            suggested_email=None,
            message=message_for_missing(),
        )

    if provider in {"yahoo", "hotmail"}:
        return DomainVerdict(
            email=clean,
            domain=domain,
            provider=provider,
            status="active",
            suggested_email=None,
            message="",
        )

    if provider in {"gmail", "apple"}:
        return DomainVerdict(
            email=clean,
            domain=domain,
            provider=provider,
            status="pending_review",
            suggested_email=None,
            message=message_for_pending(provider),
        )

    suggested = suggest_known_domain(domain)
    if suggested:
        suggested_email = f"{local}@{suggested}" if local else None
        return DomainVerdict(
            email=clean,
            domain=domain,
            provider="other",
            status="typo",
            suggested_email=suggested_email,
            message=message_for_typo(suggested),
        )

    if probe_fn(domain):
        return DomainVerdict(
            email=clean,
            domain=domain,
            provider="other",
            status="unsupported",
            suggested_email=None,
            message=message_for_unsupported(),
        )

    return DomainVerdict(
        email=clean,
        domain=domain,
        provider="other",
        status="missing",
        suggested_email=None,
        message=message_for_missing(),
    )
