"""Owner login for /admin: one-time link to an ADMIN_EMAILS inbox.

Public on purpose (the owner has no session yet). It never reveals whether
an email is an admin: the answer is always ``{"status": "sent"}``. Only
allow-listed, already-existing accounts get a mail. No Gmail scope, no
Google consent screen, no data mutation.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.admin_ops import admin_allowlist
from app.api.public_contact import client_ip
from app.database.supabase import get_supabase_client
from app.security.rate_limit import allow_request
from app.security.redirect import allowed_frontend_origins, sanitize_return_to
from app.services.donexto_verification_email import send_admin_login_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin login"])

CANONICAL_ADMIN_URL = "https://www.donexto.com/admin"


class AdminLoginLinkRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    return_to: str | None = Field(default=None, max_length=500)


def admin_return_url(return_to: str | None) -> str:
    """Always an allowed origin + ``/admin``; never the landing at ``/``."""
    safe = sanitize_return_to(return_to)
    if urlparse(safe).path.rstrip("/") == "/admin":
        return safe.rstrip("/")
    origin = f"{urlparse(safe).scheme}://{urlparse(safe).netloc}"
    if origin in allowed_frontend_origins():
        return origin + "/admin"
    return CANONICAL_ADMIN_URL


@router.post("/login-link")
def request_admin_login_link(payload: AdminLoginLinkRequest, request: Request) -> dict[str, Any]:
    email = payload.email.strip().lower()
    ip = client_ip(request)
    if not allow_request(f"admin-login-ip:{ip}", max_requests=6, window_seconds=600) or not allow_request(
        f"admin-login-email:{email}", max_requests=3, window_seconds=600
    ):
        raise HTTPException(
            status_code=429,
            detail={
                "status": "rate_limited",
                "message": "Demasiados intentos. Espera unos minutos y revisa tu correo.",
            },
        )
    if "@" in email and email in admin_allowlist():
        try:
            send_admin_login_email(
                client=get_supabase_client(),
                email=email,
                redirect_to=admin_return_url(payload.return_to),
            )
        except Exception:
            logger.error("admin_login_link_failed", exc_info=True)
    else:
        logger.info("admin_login_link_ignored_not_allowlisted")
    return {"status": "sent"}
