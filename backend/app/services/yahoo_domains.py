"""Dominios Yahoo que Donexto trata como el mismo proveedor OAuth/IMAP."""

from __future__ import annotations

# Misma identidad Yahoo (México incluido). login.yahoo.com cubre todos.
YAHOO_MAIL_DOMAINS = (
    "yahoo.com",
    "yahoo.com.mx",
    "yahoo.es",
    "ymail.com",
    "rocketmail.com",
)


def yahoo_mail_domain(email: str) -> str:
    at = (email or "").strip().lower().rfind("@")
    if at < 0:
        return ""
    return (email or "").strip().lower()[at + 1 :]


def is_yahoo_mail_address(email: str) -> bool:
    domain = yahoo_mail_domain(email)
    if not domain:
        return False
    return any(domain == root or domain.endswith("." + root) for root in YAHOO_MAIL_DOMAINS)
