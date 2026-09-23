"""Aviso a soporte cuando alguien usa un dominio real aún no integrado."""

from __future__ import annotations

import logging
import os
import smtplib
import ssl
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


class SMTPDeliveryError(RuntimeError):
    """Safe SMTP failure details for logs and controlled API errors."""

    def __init__(self, host: str, port: object, error: BaseException) -> None:
        self.error_type = type(error).__name__
        self.host = host
        self.port = port
        super().__init__(
            f"SMTP delivery failed ({self.error_type}) at {host}:{port}"
        )


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


def transactional_from_address() -> str:
    """From address for Donexto mail. Ops should set SUPPORT_SMTP_FROM."""
    return (
        os.getenv("SUPPORT_SMTP_FROM", "").strip()
        or "support@donexto.com"
    )


def _send_via_smtp(
    to_addr: str,
    subject: str,
    body: str,
    *,
    from_addr: str | None = None,
) -> bool:
    host = os.getenv("SUPPORT_SMTP_HOST", "").strip()
    if not host:
        return False
    port_value = os.getenv("SUPPORT_SMTP_PORT", "587") or "587"
    try:
        port = int(port_value)
    except (TypeError, ValueError) as error:
        logger.warning(
            "SMTP delivery failed: type=%s host=%s port=%s",
            type(error).__name__,
            host,
            port_value,
        )
        raise SMTPDeliveryError(host, port_value, error) from error
    user = os.getenv("SUPPORT_SMTP_USER", "").strip()
    password = os.getenv("SUPPORT_SMTP_PASSWORD", "").strip()
    from_addr = (from_addr or "").strip() or (
        os.getenv("SUPPORT_SMTP_FROM", "").strip()
        or user
        or "support@donexto.com"
    )
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = from_addr
    message["To"] = to_addr
    message.set_content(body)
    try:
        if port == 465:
            # Direct SSL/TLS (port 465 = SMTPS). No starttls().
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, timeout=12, context=context) as smtp:
                smtp.ehlo()
                if user and password:
                    smtp.login(user, password)
                smtp.send_message(message)
        else:
            # STARTTLS upgrade path (typical for 587).
            with smtplib.SMTP(host, port, timeout=12) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                if user and password:
                    smtp.login(user, password)
                smtp.send_message(message)
    except Exception as error:  # noqa: BLE001 — normalize without secrets
        logger.warning(
            "SMTP delivery failed: type=%s host=%s port=%s",
            type(error).__name__,
            host,
            port,
        )
        raise SMTPDeliveryError(host, port, error) from error
    return True


def _send_via_resend(
    to_addr: str,
    subject: str,
    body: str,
    *,
    from_addr: str | None = None,
) -> bool:
    """Resend HTTP API. Used when SUPPORT_SMTP_HOST is unset and RESEND_API_KEY is set."""
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    if not api_key:
        return False
    sender = (from_addr or "").strip() or transactional_from_address()
    if "<" not in sender and "@" in sender:
        sender = f"Donexto <{sender}>"
    try:
        response = httpx.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": sender,
                "to": [to_addr],
                "subject": subject,
                "text": body,
            },
            timeout=12.0,
        )
    except httpx.HTTPError as error:
        logger.warning("Resend delivery failed: type=%s", type(error).__name__)
        raise SMTPDeliveryError("api.resend.com", 443, error) from error
    if response.status_code >= 400:
        logger.warning(
            "Resend delivery failed: type=HTTPStatus host=api.resend.com port=443 status=%s",
            response.status_code,
        )
        raise SMTPDeliveryError(
            "api.resend.com",
            443,
            RuntimeError(f"HTTP {response.status_code}"),
        )
    return True


def send_transactional_email(
    to_addr: str,
    subject: str,
    body: str,
    *,
    from_addr: str | None = None,
) -> bool:
    """Send one Donexto email via SUPPORT_SMTP_* or, if unset, Resend.

    Returns False only when neither transport is configured. Transport
    failures raise ``SMTPDeliveryError`` without including secrets.
    """
    sender = (from_addr or "").strip() or transactional_from_address()
    if os.getenv("SUPPORT_SMTP_HOST", "").strip():
        return _send_via_smtp(to_addr, subject, body, from_addr=sender)
    if os.getenv("RESEND_API_KEY", "").strip():
        return _send_via_resend(to_addr, subject, body, from_addr=sender)
    return False


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
