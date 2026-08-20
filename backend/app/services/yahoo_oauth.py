"""OAuth 2.0 de Yahoo: el usuario firma en Yahoo, no escribe la clave en Donexto."""

from __future__ import annotations

import base64
import logging
from typing import Any
from urllib.parse import urlencode, urlparse

import httpx
from fastapi import HTTPException

from app.core.config import settings


logger = logging.getLogger(__name__)

YAHOO_AUTHORIZE_URL = "https://api.login.yahoo.com/oauth2/request_auth"
YAHOO_TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
YAHOO_USERINFO_URL = "https://api.login.yahoo.com/openid/v1/userinfo"
YAHOO_DEFAULT_SCOPES = "openid email profile mail-r"
YAHOO_DEFAULT_RETURN = "https://app.donexto.com/"


class YahooOAuthError(RuntimeError):
    """Fallo al hablar con Yahoo OAuth."""


def yahoo_oauth_configured() -> bool:
    return bool(
        settings.yahoo_client_id
        and settings.yahoo_client_secret
        and settings.yahoo_redirect_uri
    )


def require_yahoo_oauth_config() -> None:
    missing: list[str] = []
    if not settings.yahoo_client_id:
        missing.append("YAHOO_CLIENT_ID")
    if not settings.yahoo_client_secret:
        missing.append("YAHOO_CLIENT_SECRET")
    if not settings.yahoo_redirect_uri:
        missing.append("YAHOO_REDIRECT_URI")
    if missing:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "yahoo_oauth_not_configured",
                "message": (
                    "Donexto no pide la clave de Yahoo: te lleva a firmar "
                    "en el sitio de Yahoo. Falta crear la app OAuth en "
                    "https://developer.yahoo.com y poner en Railway: "
                    + ", ".join(missing)
                    + ". El callback debe ser "
                    "https://hms-ai-assistant-production.up.railway.app"
                    "/auth/yahoo/callback"
                ),
                "missing_variables": missing,
                "developer": "https://developer.yahoo.com/apps/",
                "mail_access": (
                    "https://senders.yahooinc.com/developer/developer-access/"
                ),
            },
        )


def sanitize_return_to(value: str | None) -> str:
    allowed = {item.rstrip("/") for item in settings.frontend_origins}
    if value:
        try:
            parsed = urlparse(value)
        except ValueError:
            parsed = None
        if parsed and parsed.scheme in {"http", "https"} and parsed.netloc:
            origin = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
            host = (parsed.hostname or "").lower()
            if origin in allowed or host.endswith("donexto.com"):
                return origin + "/"
    for item in settings.frontend_origins:
        if "donexto.com" in item.lower() and item.startswith("https://"):
            return item.rstrip("/") + "/"
    return YAHOO_DEFAULT_RETURN


def build_yahoo_authorization_url(state: str) -> str:
    require_yahoo_oauth_config()
    query = urlencode(
        {
            "client_id": settings.yahoo_client_id,
            "redirect_uri": settings.yahoo_redirect_uri,
            "response_type": "code",
            "scope": settings.yahoo_oauth_scopes,
            "state": state,
            "language": "es-mx",
        }
    )
    return f"{YAHOO_AUTHORIZE_URL}?{query}"


def _basic_auth_header() -> str:
    raw = f"{settings.yahoo_client_id}:{settings.yahoo_client_secret}".encode()
    return "Basic " + base64.b64encode(raw).decode("ascii")


def exchange_yahoo_code(code: str) -> dict[str, Any]:
    require_yahoo_oauth_config()
    try:
        response = httpx.post(
            YAHOO_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.yahoo_redirect_uri,
            },
            headers={
                "Authorization": _basic_auth_header(),
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=30.0,
        )
    except httpx.HTTPError as error:
        raise YahooOAuthError(
            "No hubo respuesta del servidor OAuth de Yahoo."
        ) from error

    if response.status_code >= 400:
        logger.warning("Yahoo token error %s: %s", response.status_code, response.text[:300])
        raise YahooOAuthError(
            "Yahoo no entregó el token. Vuelve a firmar en el sitio de Yahoo."
        )
    payload = response.json()
    if not isinstance(payload, dict) or not payload.get("access_token"):
        raise YahooOAuthError("Yahoo devolvió un token incompleto.")
    return payload


def fetch_yahoo_userinfo(access_token: str) -> dict[str, Any]:
    try:
        response = httpx.get(
            YAHOO_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30.0,
        )
    except httpx.HTTPError as error:
        raise YahooOAuthError(
            "No se pudo leer el perfil en Yahoo."
        ) from error
    if response.status_code >= 400:
        raise YahooOAuthError(
            "Yahoo no devolvió el correo de esa sesión."
        )
    payload = response.json()
    if not isinstance(payload, dict):
        raise YahooOAuthError("El perfil de Yahoo no es válido.")
    return payload


def yahoo_email_from_userinfo(userinfo: dict[str, Any]) -> str:
    email = str(userinfo.get("email") or "").strip().lower()
    if not email or "@" not in email:
        raise YahooOAuthError(
            "Yahoo no compartió el correo. En el consentimiento, "
            "autoriza el correo electrónico."
        )
    return email


def granted_mail_read(token_payload: dict[str, Any]) -> bool:
    scope = str(token_payload.get("scope") or "").lower()
    parts = {part for part in scope.replace(",", " ").split() if part}
    return bool(parts & {"mail-r", "mail-w", "mail"})
