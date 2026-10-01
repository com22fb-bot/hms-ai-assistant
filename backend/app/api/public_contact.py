"""Formulario público de la landing. Sin sesión."""

from __future__ import annotations

import logging
import re
import uuid

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.security.rate_limit import allow_request
from app.services.contact_inbox import persist_public_contact, schedule_contact_draft
from app.services.support_notify import (
    SMTPDeliveryError,
    send_public_contact_message,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/public", tags=["Public"])

# Enough for a person who retries a typo; tight enough to slow a script.
CONTACT_MAX_REQUESTS = 5
CONTACT_WINDOW_SECONDS = 600
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class PublicContactRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(default="", max_length=80)
    email: str = Field(min_length=5, max_length=120)
    country: str = Field(default="", max_length=40)
    message: str = Field(min_length=1, max_length=2000)
    lang: str = Field(default="", max_length=12)
    # Honeypot. Humans leave it empty; bots often fill every input.
    website: str = Field(default="", max_length=500)

    @field_validator("email")
    @classmethod
    def _valid_email(cls, value: str) -> str:
        email = value.strip().lower()
        if not _EMAIL_RE.fullmatch(email):
            raise ValueError("invalid email")
        return email

    @field_validator("name", "country", "lang")
    @classmethod
    def _single_line(cls, value: str) -> str:
        return " ".join(value.replace("\r", " ").replace("\n", " ").split())


def client_ip(request: Request) -> str:
    """Visitor address for the rate limit.

    Uvicorn on Railway is started without ``--proxy-headers``, so
    ``request.client.host`` is the proxy. Railway puts the visitor in
    ``X-Forwarded-For``.
    """
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first[:80]
    real_ip = request.headers.get("x-real-ip", "").strip()
    if real_ip:
        return real_ip[:80]
    host = getattr(getattr(request, "client", None), "host", None) or "unknown"
    return str(host)[:80]


@router.post("/contact")
def submit_public_contact(
    payload: PublicContactRequest,
    request: Request,
) -> dict[str, str]:
    ip = client_ip(request)
    if not allow_request(
        f"public-contact:{ip}",
        max_requests=CONTACT_MAX_REQUESTS,
        window_seconds=CONTACT_WINDOW_SECONDS,
    ):
        raise HTTPException(
            status_code=429,
            detail={
                "status": "rate_limited",
                "message": (
                    "Demasiados mensajes seguidos. Espera un momento "
                    "o escribe a support@donexto.com."
                ),
            },
        )

    if payload.website:
        logger.info("Contact honeypot tripped from %s", ip)
        return {"status": "ok"}

    message_id = str(uuid.uuid4())
    try:
        delivered = send_public_contact_message(
            name=payload.name,
            email=payload.email,
            country=payload.country,
            message=payload.message,
            lang=payload.lang,
            message_id=message_id,
        )
    except SMTPDeliveryError:
        logger.warning("Public contact delivery failed")
        raise HTTPException(
            status_code=502,
            detail={
                "status": "delivery_failed",
                "message": "No se pudo enviar el mensaje.",
            },
        ) from None

    if not delivered:
        logger.warning("Public contact skipped: Resend is not configured")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "delivery_unconfigured",
                "message": "El envío de contacto no está configurado.",
            },
        )

    stored = persist_public_contact(
        message_id=message_id,
        name=payload.name,
        email=payload.email,
        country=payload.country,
        message=payload.message,
        lang=payload.lang,
        ip=ip,
    )
    if stored:
        schedule_contact_draft(stored)

    return {"status": "ok"}
