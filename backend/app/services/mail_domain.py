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

# Solo leemos buzón cuando hay OAuth + Mail.Read en producción: Microsoft.
ACTIVE_OPTIONS_TEXT = "Outlook, Hotmail, Live, MSN y Microsoft 365"
PENDING_OPTIONS_TEXT = "Gmail, Google Workspace, Yahoo e iCloud"

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


KNOWN_ACTIVE_DOMAINS = _roots_for(MICROSOFT_MAIL_DOMAINS)
KNOWN_PENDING_DOMAINS = _roots_for(
    GMAIL_MAIL_DOMAINS, YAHOO_MAIL_DOMAINS, APPLE_MAIL_DOMAINS
)
KNOWN_MAIL_DOMAINS = _roots_for(KNOWN_ACTIVE_DOMAINS, KNOWN_PENDING_DOMAINS)

MICROSOFT_MX_MARKERS = (
    "mail.protection.outlook.com",
    "olc.protection.outlook.com",
    "outlook.com",
    "hotmail.com",
)
GOOGLE_MX_MARKERS = (
    "aspmx.l.google.com",
    "googlemail.com",
    "google.com",
)


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


def _mx_marker_hit(hosts: list[str], markers: tuple[str, ...]) -> bool:
    return any(
        any(host == marker or host.endswith("." + marker) for marker in markers)
        for host in hosts
    )


def is_microsoft365_mx(hosts: list[str]) -> bool:
    return _mx_marker_hit([h.lower().rstrip(".") for h in hosts], MICROSOFT_MX_MARKERS)


def is_google_workspace_mx(hosts: list[str]) -> bool:
    return _mx_marker_hit([h.lower().rstrip(".") for h in hosts], GOOGLE_MX_MARKERS)


def lookup_mx_hosts(
    domain: str,
    timeout_seconds: float = 1.5,
) -> list[str]:
    """MX del dominio (minúsculas). Vacío si no hay respuesta o el lookup falla."""
    if not is_plausible_hostname(domain):
        return []

    def _query() -> list[str]:
        try:
            import dns.resolver  # type: ignore[import-not-found]

            answers = dns.resolver.resolve(domain, "MX", lifetime=timeout_seconds)
            hosts = [
                str(getattr(item, "exchange", "")).rstrip(".").lower()
                for item in answers
            ]
            return [host for host in hosts if host]
        except Exception:
            return _lookup_mx_udp(domain, timeout_seconds)

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_query)
        try:
            return list(future.result(timeout=timeout_seconds + 0.4))
        except (FutureTimeout, OSError):
            return []


def _lookup_mx_udp(domain: str, timeout_seconds: float) -> list[str]:
    """Consulta MX mínima (RFC 1035) a 8.8.8.8. Sin dependencias extra."""
    import random
    import struct

    labels = domain.strip(".").split(".")
    if not labels:
        return []
    query = struct.pack("!HHHHHH", random.randint(1, 65535), 0x0100, 1, 0, 0, 0)
    for label in labels:
        encoded = label.encode("idna", errors="ignore")
        if not encoded or len(encoded) > 63:
            return []
        query += bytes([len(encoded)]) + encoded
    query += b"\x00" + struct.pack("!HH", 15, 1)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout_seconds)
        sock.sendto(query, ("8.8.8.8", 53))
        data, _ = sock.recvfrom(512)
        sock.close()
    except OSError:
        return []
    if len(data) < 12:
        return []
    _, flags, qs, answers, _, _ = struct.unpack("!HHHHHH", data[:12])
    if flags & 0x000F or qs != 1 or answers == 0:
        return []

    def _skip_name(buf: bytes, offset: int) -> int:
        while offset < len(buf):
            length = buf[offset]
            if length == 0:
                return offset + 1
            if length & 0xC0 == 0xC0:
                return offset + 2
            offset += 1 + length
        return offset

    offset = _skip_name(data, 12) + 4
    hosts: list[str] = []
    for _ in range(answers):
        offset = _skip_name(data, offset)
        if offset + 10 > len(data):
            break
        rtype, _, _, rdlength = struct.unpack("!HHIH", data[offset : offset + 10])
        offset += 10
        rdata = data[offset : offset + rdlength]
        offset += rdlength
        if rtype != 15 or len(rdata) < 3:
            continue
        name_off = 2
        parts: list[str] = []
        jumped = False
        cursor = name_off
        hops = 0
        while hops < 16 and cursor < len(rdata):
            hops += 1
            length = rdata[cursor]
            if length == 0:
                break
            if length & 0xC0 == 0xC0:
                pointer = ((length & 0x3F) << 8) + (rdata[cursor + 1] if cursor + 1 < len(rdata) else 0)
                if not jumped:
                    cursor = pointer
                    jumped = True
                    # Pointers refer to the full packet, not rdata.
                    packet_cursor = pointer
                    packet_parts: list[str] = []
                    while packet_cursor < len(data) and hops < 16:
                        hops += 1
                        plen = data[packet_cursor]
                        if plen == 0:
                            break
                        if plen & 0xC0 == 0xC0:
                            packet_cursor = ((plen & 0x3F) << 8) + data[packet_cursor + 1]
                            continue
                        packet_parts.append(
                            data[packet_cursor + 1 : packet_cursor + 1 + plen].decode(
                                "ascii", errors="ignore"
                            )
                        )
                        packet_cursor += 1 + plen
                    parts.extend(packet_parts)
                    break
            parts.append(rdata[cursor + 1 : cursor + 1 + length].decode("ascii", errors="ignore"))
            cursor += 1 + length
        host = ".".join(p for p in parts if p).lower().rstrip(".")
        if host:
            hosts.append(host)
    return hosts


ACTIVE_OPTIONS_MESSAGE = (
    f"Ahora sí leemos: {ACTIVE_OPTIONS_TEXT}. "
    f"{PENDING_OPTIONS_TEXT}: Pronto / Próximamente."
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


def provider_coming_soon_label(provider: str) -> str:
    return {
        "gmail": "Gmail",
        "yahoo": "Yahoo",
        "apple": "iCloud",
    }.get(provider, "ese correo")


def message_for_pending(provider: str) -> str:
    label = provider_coming_soon_label(provider)
    return (
        f"Próximamente. Donexto todavía no puede monitorear {label}. "
        f"Opciones activas ahora: {ACTIVE_OPTIONS_TEXT}. "
        f"{PENDING_OPTIONS_TEXT}: te avisamos si te apuntas a la lista."
    )


def message_for_unsupported() -> str:
    return (
        "Donexto solo monitorea Microsoft 365 y (pronto) Google Workspace. "
        "Otros servidores de empresa aún no se pueden leer. "
        "Si quieres, te avisamos cuando haya soporte para ese dominio. "
        f"Ahora sí leemos: {ACTIVE_OPTIONS_TEXT}."
    )


def coming_soon_next(provider: str) -> str:
    return {
        "gmail": "coming_soon_gmail",
        "yahoo": "coming_soon_yahoo",
        "apple": "coming_soon_icloud",
    }.get(provider, "waitlist")


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
            return coming_soon_next(self.provider)
        if self.status == "unsupported":
            return "unsupported_imap_domain"
        return "signup"


ProbeFn = Callable[[str], bool]
MxProbeFn = Callable[[str], list[str]]


def classify_mail_domain(
    email: str,
    *,
    probe: ProbeFn | None = None,
    mx_probe: MxProbeFn | None = None,
) -> DomainVerdict:
    clean = (email or "").strip().lower()
    domain = email_domain(clean)
    local = email_local_part(clean)
    provider = provider_for_domain(domain)
    probe_fn = probe or domain_has_mail_records
    mx_fn = mx_probe or lookup_mx_hosts

    if not domain or not local or not is_plausible_hostname(domain):
        return DomainVerdict(
            email=clean,
            domain=domain,
            provider="other",
            status="missing",
            suggested_email=None,
            message=message_for_missing(),
        )

    if provider == "hotmail":
        return DomainVerdict(
            email=clean,
            domain=domain,
            provider=provider,
            status="active",
            suggested_email=None,
            message="",
        )

    if provider in {"gmail", "yahoo", "apple"}:
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

    mx_hosts = mx_fn(domain)
    if is_microsoft365_mx(mx_hosts):
        return DomainVerdict(
            email=clean,
            domain=domain,
            provider="hotmail",
            status="active",
            suggested_email=None,
            message="",
        )
    if is_google_workspace_mx(mx_hosts):
        return DomainVerdict(
            email=clean,
            domain=domain,
            provider="gmail",
            status="pending_review",
            suggested_email=None,
            message=message_for_pending("gmail"),
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
