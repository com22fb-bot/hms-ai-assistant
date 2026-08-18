"""Consulta pública: ¿este correo ya tiene cuenta Donexto?"""

from __future__ import annotations

import time
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.donexto_account_lookup import (
    admin_users_exist,
    normalize_lookup_email,
)


router = APIRouter(prefix="/auth", tags=["Donexto account"])

_WINDOW_SECONDS = 60.0
_MAX_HITS = 20
_hits: dict[str, list[float]] = {}


class AccountLookupRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("cf-connecting-ip") or request.headers.get(
        "x-forwarded-for",
        "",
    )
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    return request.client.host if request.client else "unknown"


def _allow(ip: str) -> bool:
    now = time.monotonic()
    recent = [stamp for stamp in _hits.get(ip, []) if now - stamp < _WINDOW_SECONDS]
    if len(recent) >= _MAX_HITS:
        _hits[ip] = recent
        return False
    recent.append(now)
    _hits[ip] = recent
    return True


@router.post("/donexto-account")
def donexto_account_lookup(
    payload: AccountLookupRequest,
    request: Request,
) -> dict[str, bool]:
    if not _allow(_client_ip(request)):
        raise HTTPException(
            status_code=429,
            detail={
                "status": "rate_limited",
                "message": "Demasiadas consultas seguidas. Espera un momento.",
            },
        )

    email = normalize_lookup_email(payload.email)
    if not email:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "invalid_email",
                "message": "Escribe un correo válido.",
            },
        )

    base = settings.supabase_url.rstrip("/")
    secret = settings.supabase_secret_key
    if not base or not secret:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_configured",
                "message": "No fue posible comprobar la cuenta Donexto.",
            },
        )

    url = f"{base}/auth/v1/admin/users"
    try:
        response = httpx.get(
            url,
            params={"email": email},
            headers={
                "apikey": secret,
                "Authorization": f"Bearer {secret}",
            },
            timeout=8.0,
        )
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=502,
            detail={
                "status": "lookup_failed",
                "message": "No fue posible comprobar si el correo ya tiene cuenta.",
            },
        ) from error

    if response.status_code == 404:
        return {"exists": False}

    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail={
                "status": "lookup_failed",
                "message": "No fue posible comprobar si el correo ya tiene cuenta.",
            },
        )

    try:
        body: Any = response.json()
    except ValueError as error:
        raise HTTPException(
            status_code=502,
            detail={
                "status": "lookup_failed",
                "message": "No fue posible comprobar si el correo ya tiene cuenta.",
            },
        ) from error

    return {"exists": admin_users_exist(body, email)}
