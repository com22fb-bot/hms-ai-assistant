"""OAuth 2.0 de Microsoft: Outlook, Hotmail y Microsoft 365.

El usuario firma en login.microsoftonline.com. Donexto no pide la clave.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.services.yahoo_oauth import (
    sanitize_login_hint,
    sanitize_return_to,
)


logger = logging.getLogger(__name__)

MICROSOFT_AUTHORIZE_URL = (
    "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
)
MICROSOFT_TOKEN_URL = (
    "https://login.microsoftonline.com/common/oauth2/v2.0/token"
)
MICROSOFT_GRAPH_ME_URL = "https://graph.microsoft.com/v1.0/me"
MICROSOFT_IDENTITY_SCOPES = "openid email profile offline_access User.Read"
MICROSOFT_MAIL_SCOPE = "Mail.Read"
MICROSOFT_SIGNUP_VIA = "microsoft_oauth"


class MicrosoftOAuthError(RuntimeError):
    """Fallo al hablar con Microsoft OAuth o Graph."""


def microsoft_oauth_configured() -> bool:
    return bool(
        settings.azure_client_id
        and settings.azure_client_secret
        and settings.azure_redirect_uri
    )


def require_microsoft_oauth_config() -> None:
    missing: list[str] = []
    if not settings.azure_client_id:
        missing.append("AZURE_CLIENT_ID")
    if not settings.azure_client_secret:
        missing.append("AZURE_CLIENT_SECRET")
    if not settings.azure_redirect_uri:
        missing.append("AZURE_REDIRECT_URI")
    if missing:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "microsoft_oauth_not_configured",
                "message": (
                    "Donexto no pide la clave de Outlook: te lleva a firmar "
                    "en el sitio de Microsoft. Falta crear la app en Entra "
                    "(cuentas personales y de organización) y poner en "
                    "Railway: "
                    + ", ".join(missing)
                    + ". El callback debe ser "
                    "https://hms-ai-assistant-production.up.railway.app"
                    "/auth/microsoft/callback"
                ),
                "missing_variables": missing,
                "developer": "https://entra.microsoft.com/",
            },
        )


def microsoft_authorize_scopes() -> str:
    """Identidad + lectura de correo. Mail.Read es consentimiento Graph, no un alcance restringido tipo Yahoo."""
    return f"{MICROSOFT_IDENTITY_SCOPES} {MICROSOFT_MAIL_SCOPE}"


def build_microsoft_authorization_url(
    state: str,
    login_hint: str | None = None,
) -> str:
    require_microsoft_oauth_config()
    query: dict[str, str] = {
        "client_id": settings.azure_client_id,
        "redirect_uri": settings.azure_redirect_uri,
        "response_type": "code",
        "response_mode": "query",
        "scope": microsoft_authorize_scopes(),
        "state": state,
        "prompt": "select_account",
    }
    hint = sanitize_login_hint(login_hint)
    if hint:
        query["login_hint"] = hint
    return f"{MICROSOFT_AUTHORIZE_URL}?{urlencode(query)}"


def exchange_microsoft_code(code: str) -> dict[str, Any]:
    require_microsoft_oauth_config()
    try:
        response = httpx.post(
            MICROSOFT_TOKEN_URL,
            data={
                "client_id": settings.azure_client_id,
                "client_secret": settings.azure_client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.azure_redirect_uri,
                "scope": microsoft_authorize_scopes(),
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30.0,
        )
    except httpx.HTTPError as error:
        raise MicrosoftOAuthError(
            "No hubo respuesta del servidor OAuth de Microsoft."
        ) from error

    if response.status_code >= 400:
        logger.warning(
            "Microsoft token error %s: %s",
            response.status_code,
            response.text[:300],
        )
        raise MicrosoftOAuthError(
            "Microsoft no entregó el token. Vuelve a firmar en el sitio de Microsoft."
        )
    payload = response.json()
    if not isinstance(payload, dict) or not payload.get("access_token"):
        raise MicrosoftOAuthError("Microsoft devolvió un token incompleto.")
    return payload


def fetch_microsoft_profile(access_token: str) -> dict[str, Any]:
    try:
        response = httpx.get(
            MICROSOFT_GRAPH_ME_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30.0,
        )
    except httpx.HTTPError as error:
        raise MicrosoftOAuthError(
            "No se pudo leer el perfil en Microsoft."
        ) from error
    if response.status_code >= 400:
        raise MicrosoftOAuthError(
            "Microsoft no devolvió el correo de esa sesión."
        )
    payload = response.json()
    if not isinstance(payload, dict):
        raise MicrosoftOAuthError("El perfil de Microsoft no es válido.")
    return payload


def microsoft_email_from_profile(profile: dict[str, Any]) -> str:
    for key in ("mail", "userPrincipalName", "user_principal_name"):
        email = str(profile.get(key) or "").strip().lower()
        if email and "@" in email and not email.endswith("#ext#"):
            return email.split("#")[0]
    raise MicrosoftOAuthError(
        "Microsoft no compartió el correo. En el consentimiento, "
        "autoriza el correo electrónico."
    )


def granted_microsoft_mail_read(token_payload: dict[str, Any]) -> bool:
    scope = str(token_payload.get("scope") or "").lower().replace(",", " ")
    return "mail.read" in scope


def refresh_microsoft_tokens(refresh_token: str) -> dict[str, Any]:
    require_microsoft_oauth_config()
    try:
        response = httpx.post(
            MICROSOFT_TOKEN_URL,
            data={
                "client_id": settings.azure_client_id,
                "client_secret": settings.azure_client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "scope": microsoft_authorize_scopes(),
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30.0,
        )
    except httpx.HTTPError as error:
        raise MicrosoftOAuthError(
            "No hubo respuesta al renovar la sesión de Microsoft."
        ) from error
    if response.status_code >= 400:
        logger.warning(
            "Microsoft refresh error %s: %s",
            response.status_code,
            response.text[:300],
        )
        raise MicrosoftOAuthError(
            "Microsoft pidió firmar de nuevo. Vuelve al sitio de Microsoft."
        )
    payload = response.json()
    if not isinstance(payload, dict) or not payload.get("access_token"):
        raise MicrosoftOAuthError("Microsoft devolvió un token incompleto.")
    return payload


def graph_get(
    access_token: str,
    url: str,
    *,
    params: dict[str, str] | None = None,
) -> dict[str, Any]:
    try:
        response = httpx.get(
            url,
            params=params,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=45.0,
        )
    except httpx.HTTPError as error:
        raise MicrosoftOAuthError(
            "No hubo respuesta de Microsoft Graph."
        ) from error
    if response.status_code >= 400:
        raise MicrosoftOAuthError(
            f"graph_http_{response.status_code}:{response.text[:240]}"
        )
    payload = response.json()
    if not isinstance(payload, dict):
        raise MicrosoftOAuthError("Microsoft Graph devolvió un cuerpo inválido.")
    return payload
