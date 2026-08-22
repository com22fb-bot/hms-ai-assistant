"""Aviso a soporte cuando alguien usa un dominio real aún no integrado."""

from __future__ import annotations

import logging
import os
import smtplib
import threading
import time
from email.message import EmailMessage
from typing import Callable

import httpx

logger = logging.getLogger(__name__)

DEFAULT_SUPPORT_EMAIL = "support@yahoo.com"
_NOTIFY_COOLDOWN_SECONDS = 24 * 60 * 60
_recent_domains: dict[str, float] = {}
_recent_lock = threading.Lock()


def support_notify_email() -> str:
    return (
        os.getenv("SUPPORT_NOTIFY_EMAIL", DEFAULT_SUPPORT_EMAIL).strip()
        or DEFAULT_SUPPORT_EMAIL
    )


def _within_cooldown(domain: str) -> bool:
    now = time.monotonic()
    with _recent_lock:
        last = _recent_domains.get(domain)
        if last is not None and (now - last) < _NOTIFY_COOLDOWN_SECONDS:
            return True
        _recent_domains[domain] = now
        return False


def _send_via_smtp(to_addr: str, subject: str, body: str) -> bool:
    host = os.getenv("SUPPORT_SMTP_HOST", "").strip()
    if not host:
        return False
    port = int(os.getenv("SUPPORT_SMTP_PORT", "587") or "587")
    user = os.getenv("SUPPORT_SMTP_USER", "").strip()
    password = os.getenv("SUPPORT_SMTP_PASSWORD", "").strip()
    from_addr = (
        os.getenv("SUPPORT_SMTP_FROM", "").strip()
        or user
        or "noreply@donexto.com"
    )
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = from_addr
    message["To"] = to_addr
    message.set_content(body)
    with smtplib.SMTP(host, port, timeout=12) as smtp:
        smtp.ehlo()
        try:
            smtp.starttls()
            smtp.ehlo()
        except smtplib.SMTPException:
            pass
        if user and password:
            smtp.login(user, password)
        smtp.send_message(message)
    return True


def _send_via_formsubmit(to_addr: str, subject: str, body: str) -> bool:
    """Fallback sin SMTP: FormSubmit confirma una vez el buzón y reenvía."""
    url = f"https://formsubmit.co/ajax/{to_addr}"
    response = httpx.post(
        url,
        json={
            "_subject": subject,
            "message": body,
            "_template": "box",
            "_captcha": "false",
        },
        headers={"Accept": "application/json"},
        timeout=10.0,
    )
    response.raise_for_status()
    return True


def persist_domain_request(email: str, domain: str, notified_to: str) -> None:
    try:
        from app.database.supabase import get_supabase_client

        get_supabase_client().table("domain_integration_requests").insert(
            {
                "email": email,
                "domain": domain,
                "notified_to": notified_to,
            }
        ).execute()
    except Exception as error:  # noqa: BLE001 — la tabla puede no existir aún
        logger.info("No se persistió domain_integration_requests: %s", error)


def send_unsupported_domain_notice(email: str, domain: str) -> bool:
    to_addr = support_notify_email()
    subject = f"Donexto: dominio por integrar — {domain}"
    body = (
        "Alguien intentó entrar a Donexto con un correo cuyo dominio "
        "existe, pero aún no está integrado.\n\n"
        f"Correo: {email}\n"
        f"Dominio: {domain}\n\n"
        "No hay trámite hecho para ese proveedor. Revisa si conviene "
        "integrarlo (OAuth / lectura de buzón).\n"
    )
    persist_domain_request(email, domain, to_addr)
    try:
        if _send_via_smtp(to_addr, subject, body):
            return True
    except Exception as error:  # noqa: BLE001
        logger.warning("SMTP de soporte falló: %s", error)
    try:
        return _send_via_formsubmit(to_addr, subject, body)
    except Exception as error:  # noqa: BLE001
        logger.warning("Aviso a soporte no se pudo enviar: %s", error)
        return False


def notify_unsupported_domain_async(
    email: str,
    domain: str,
    sender: Callable[[str, str], bool] | None = None,
) -> bool:
    """Devuelve True si se encola el aviso (una vez por dominio al día)."""
    clean_domain = (domain or "").strip().lower()
    if not clean_domain or _within_cooldown(clean_domain):
        return False
    send = sender or send_unsupported_domain_notice

    def _run() -> None:
        try:
            send(email, clean_domain)
        except Exception as error:  # noqa: BLE001
            logger.warning("Hilo de aviso a soporte falló: %s", error)

    threading.Thread(target=_run, daemon=True, name="donexto-support-notify").start()
    return True
