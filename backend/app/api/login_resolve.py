from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.mail_domain import classify_mail_domain, provider_for_domain
from app.services.support_notify import notify_unsupported_domain_async
from app.services.yahoo_session import auth_user_exists


router = APIRouter(prefix="/auth/login", tags=["Login"])


class LoginResolveRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)


def resolve_mailbox_provider(email: str) -> str:
    from app.services.mail_domain import email_domain

    return provider_for_domain(email_domain(email))


def next_for_existing(provider: str) -> str:
    return {
        "gmail": "google_oauth",
        "yahoo": "yahoo_oauth",
        "hotmail": "azure_oauth",
        "apple": "apple_oauth",
    }.get(provider, "magiclink")


@router.post("/resolve")
def resolve_login(payload: LoginResolveRequest) -> dict[str, object]:
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
        message = ""
    elif verdict.status == "unsupported":
        nxt = "unsupported"
        message = verdict.message
        notified = notify_unsupported_domain_async(email, verdict.domain)
    elif verdict.status in {"typo", "missing", "pending_review"}:
        nxt = verdict.next_when_unknown
        message = verdict.message
    else:
        nxt = "signup"
        message = ""

    return {
        "status": "ok",
        "email": email,
        "exists": exists,
        "provider": verdict.provider,
        "domain": verdict.domain,
        "domain_status": verdict.status if not exists else "active",
        "next": nxt,
        "suggested_email": verdict.suggested_email,
        "message": message,
        "notified_support": notified,
        "active_options": ["yahoo", "hotmail"],
        "pending_options": ["gmail", "apple"],
    }
