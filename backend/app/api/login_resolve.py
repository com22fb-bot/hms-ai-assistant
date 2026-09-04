from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.security.rate_limit import allow_request
from app.services.mail_domain import (
    classify_mail_domain,
    coming_soon_next,
    provider_for_domain,
)
from app.services.mailbox_waitlist import persist_waitlist
from app.services.support_notify import notify_unsupported_domain_async
from app.services.yahoo_session import auth_user_exists


router = APIRouter(prefix="/auth/login", tags=["Login"])

ACTIVE_OPTIONS = ["hotmail"]
PENDING_OPTIONS = ["gmail", "yahoo", "apple"]
ACCOUNT_EXISTS_NEXT = frozenset(
    {
        "yahoo_oauth",
        "google_oauth",
        "azure_oauth",
        "apple_oauth",
    }
)


class LoginResolveRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)


class WaitlistRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    provider: str = Field(min_length=2, max_length=40)


def resolve_mailbox_provider(email: str) -> str:
    from app.services.mail_domain import email_domain

    return provider_for_domain(email_domain(email))


def next_for_existing(provider: str) -> str:
    """Cuentas ya creadas: identity login. No fingir lectura de buzón."""
    return {
        "gmail": "google_oauth",
        "yahoo": "yahoo_oauth",
        "hotmail": "azure_oauth",
        "apple": "coming_soon_icloud",
    }.get(provider, "waitlist")


def next_for_unknown(verdict) -> str:
    if verdict.status == "active" and verdict.provider == "hotmail":
        return "signup"
    if verdict.status == "pending_review":
        return coming_soon_next(verdict.provider)
    if verdict.status == "unsupported":
        return "unsupported_imap_domain"
    return verdict.next_when_unknown


@router.post("/resolve")
def resolve_login(payload: LoginResolveRequest, request: Request) -> dict[str, object]:
    client_host = getattr(getattr(request, "client", None), "host", None) or "unknown"
    if not allow_request(f"login-resolve:{client_host}"):
        raise HTTPException(
            status_code=429,
            detail={
                "status": "rate_limited",
                "message": "Demasiados intentos seguidos. Espera un momento.",
            },
        )

    email = payload.email.strip().lower()
    verdict = classify_mail_domain(email)
    if "@" not in email or not verdict.domain:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "invalid_email",
                "message": "Escribe un correo válido.",
            },
        )

    exists = auth_user_exists(email)
    notified = False
    if exists:
        nxt = next_for_existing(verdict.provider)
        message = verdict.message if nxt.startswith("coming_soon") else ""
        if nxt == "waitlist":
            message = verdict.message or (
                "Donexto solo monitorea Microsoft 365 y (pronto) Google Workspace. "
                "Otros servidores de empresa aún no se pueden leer."
            )
    elif verdict.status == "active":
        nxt = "signup"
        message = ""
    elif verdict.status == "unsupported":
        nxt = "unsupported_imap_domain"
        message = verdict.message
        notified = notify_unsupported_domain_async(email, verdict.domain)
    else:
        nxt = next_for_unknown(verdict)
        message = verdict.message

    return {
        "status": "ok",
        "email": email,
        "provider": verdict.provider,
        "domain": verdict.domain,
        "domain_status": verdict.status if nxt not in ACCOUNT_EXISTS_NEXT else "active",
        "next": nxt,
        "suggested_email": verdict.suggested_email,
        "message": message,
        "notified_support": notified,
        "active_options": ACTIVE_OPTIONS,
        "pending_options": PENDING_OPTIONS,
        "read_available": verdict.provider == "hotmail" and verdict.status == "active",
    }


@router.post("/waitlist")
def join_waitlist(payload: WaitlistRequest) -> dict[str, object]:
    email = payload.email.strip().lower()
    if "@" not in email:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "invalid_email",
                "message": "Escribe un correo válido.",
            },
        )
    stored = persist_waitlist(email, payload.provider)
    return {
        **stored,
        "message": stored.get("message")
        or (
            "Te avisamos a este correo cuando Donexto pueda monitorear "
            "ese buzón."
        ),
    }
