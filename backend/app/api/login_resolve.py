"""Ruteo de login: si el correo ya existe, al proveedor; si no, a crear cuenta."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.yahoo_session import auth_user_exists


router = APIRouter(prefix="/auth/login", tags=["Login"])

_GMAIL = ("gmail.com", "googlemail.com")
_YAHOO = (
    "yahoo.com",
    "yahoo.com.mx",
    "yahoo.es",
    "ymail.com",
    "rocketmail.com",
)
_HOTMAIL = (
    "hotmail.com",
    "hotmail.es",
    "outlook.com",
    "outlook.es",
    "live.com",
    "msn.com",
)
_APPLE = ("icloud.com", "me.com", "mac.com")


class LoginResolveRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)


def _domain(email: str) -> str:
    at = email.rfind("@")
    if at < 0:
        return ""
    return email[at + 1 :]


def _matches(domain: str, roots: tuple[str, ...]) -> bool:
    return any(domain == root or domain.endswith("." + root) for root in roots)


def resolve_mailbox_provider(email: str) -> str:
    domain = _domain(email)
    if not domain:
        return "other"
    if _matches(domain, _GMAIL):
        return "gmail"
    if _matches(domain, _YAHOO):
        return "yahoo"
    if _matches(domain, _HOTMAIL):
        return "hotmail"
    if _matches(domain, _APPLE):
        return "apple"
    return "other"


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
    domain = _domain(email)
    if "@" not in email or "." not in domain:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "invalid_email",
                "message": "Escribe un correo válido.",
            },
        )

    provider = resolve_mailbox_provider(email)
    exists = auth_user_exists(email)
    nxt = next_for_existing(provider) if exists else "signup"
    return {
        "status": "ok",
        "email": email,
        "exists": exists,
        "provider": provider,
        "next": nxt,
    }
