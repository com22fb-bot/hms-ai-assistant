"""Verificación de Cloudflare Turnstile para formularios públicos."""

from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def turnstile_passed(token: str, remote_ip: str | None = None) -> bool:
    """True si Turnstile aprueba el token.

    Sin ``TURNSTILE_SECRET_KEY`` no se exige (despliegue por partes). Si
    Cloudflare no responde, se deja pasar: el límite de intentos sigue activo
    y un caído de Turnstile no debe tumbar el formulario.
    """
    secret = os.getenv("TURNSTILE_SECRET_KEY", "").strip()
    if not secret:
        return True
    if not token:
        return False
    data = {"secret": secret, "response": token}
    if remote_ip and remote_ip != "unknown":
        data["remoteip"] = remote_ip
    try:
        response = httpx.post(SITEVERIFY_URL, data=data, timeout=8.0)
        payload = response.json()
    except Exception:  # noqa: BLE001
        logger.warning("Turnstile siteverify unavailable; allowing request")
        return True
    if not payload.get("success"):
        logger.info("Turnstile rejected: %s", payload.get("error-codes"))
        return False
    return True
