"""Dominios Microsoft que Donexto trata como Outlook / Hotmail / Microsoft 365."""

from __future__ import annotations

# Consumidor (Outlook/Hotmail) + inquilino clásico de Microsoft 365.
MICROSOFT_CONSUMER_DOMAINS = (
    "hotmail.com",
    "hotmail.es",
    "hotmail.com.mx",
    "outlook.com",
    "outlook.es",
    "outlook.com.mx",
    "live.com",
    "live.com.mx",
    "msn.com",
)
MICROSOFT_WORK_DOMAINS = ("onmicrosoft.com",)
MICROSOFT_MAIL_DOMAINS = MICROSOFT_CONSUMER_DOMAINS + MICROSOFT_WORK_DOMAINS


def microsoft_mail_domain(email: str) -> str:
    at = (email or "").strip().lower().rfind("@")
    if at < 0:
        return ""
    return (email or "").strip().lower()[at + 1 :]


def _matches(domain: str, roots: tuple[str, ...]) -> bool:
    return any(domain == root or domain.endswith("." + root) for root in roots)


def is_microsoft_mail_address(email: str) -> bool:
    domain = microsoft_mail_domain(email)
    if not domain:
        return False
    return _matches(domain, MICROSOFT_MAIL_DOMAINS)


def is_personal_microsoft_address(email: str) -> bool:
    domain = microsoft_mail_domain(email)
    return bool(domain) and _matches(domain, MICROSOFT_CONSUMER_DOMAINS)
