"""OAuth 2.0 de Yahoo: el usuario firma en Yahoo, no escribe la clave en Donexto."""

from __future__ import annotations

import base64
import logging
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.security.redirect import YAHOO_DEFAULT_RETURN, sanitize_return_to

__all__ = ["sanitize_return_to", "YAHOO_DEFAULT_RETURN"]


logger = logging.getLogger(__name__)

YAHOO_AUTHORIZE_URL = "https://api.login.yahoo.com/oauth2/request_auth"
YAHOO_TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
YAHOO_USERINFO_URL = "https://api.login.yahoo.com/openid/v1/userinfo"
YAHOO_DEFAULT_SCOPES = "openid email profile"
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


YAHOO_OAUTH_INTENTS = frozenset({"login", "signup", "mailbox"})


def normalize_yahoo_intent(value: str | None) -> str:
    """login/signup = identidad; mailbox = pedir lectura del buzón."""
    clean = (value or "login").strip().lower()
    return clean if clean in YAHOO_OAUTH_INTENTS else "login"


def yahoo_authorize_scopes(intent: str) -> str:
    """Identidad siempre. mail-r solo en intent=mailbox y si Yahoo ya lo aprobó."""
    configured = (settings.yahoo_oauth_scopes or YAHOO_DEFAULT_SCOPES).strip()
    parts = [part for part in configured.replace(",", " ").split() if part]
    identity = [
        part for part in parts if part.lower() != "mail-r"
    ] or YAHOO_DEFAULT_SCOPES.split()
    if intent == "mailbox" and settings.yahoo_mail_read_enabled:
        return " ".join([*identity, "mail-r"])
    return " ".join(identity)


def yahoo_intent_from_state(state: str) -> str:
    prefix, separator, _rest = (state or "").partition(".")
    if separator and prefix in YAHOO_OAUTH_INTENTS:
        return prefix
    return "login"


def sanitize_login_hint(value: str | None) -> str | None:
    clean = (value or "").strip().lower()
    if "@" not in clean or len(clean) > 320:
        return None
    domain = clean.rsplit("@", 1)[-1]
    if "." not in domain:
        return None
    return clean


HINT_STATE_MARKER = "h"


def encode_login_hint_in_state_prefix(
    prefix: str,
    login_hint: str | None,
) -> str:
    """Embed the expected mailbox email in the OAuth state for callback checks."""
    hint = sanitize_login_hint(login_hint)
    if not hint:
        return prefix
    encoded = base64.urlsafe_b64encode(hint.encode()).decode().rstrip("=")
    return f"{prefix}.{HINT_STATE_MARKER}.{encoded}"


def login_hint_from_oauth_state(state: str) -> str | None:
    parts = (state or "").split(".")
    for index, part in enumerate(parts[:-1]):
        if part != HINT_STATE_MARKER:
            continue
        encoded = parts[index + 1] if index + 1 < len(parts) else ""
        if not encoded:
            return None
        try:
            padding = "=" * (-len(encoded) % 4)
            decoded = base64.urlsafe_b64decode(f"{encoded}{padding}").decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return None
        return sanitize_login_hint(decoded)
    return None


def oauth_email_mismatch_message(
    expected_hint: str | None,
    actual_email: str,
    *,
    provider_label: str = "el proveedor",
) -> str | None:
    """Return a user-facing error when OAuth identity != email typed in Donexto."""
    expected = sanitize_login_hint(expected_hint)
    if not expected:
        return None
    actual = (actual_email or "").strip().lower()
    if actual == expected:
        return None
    return (
        f"Firmaste con {actual}, pero en Donexto pediste {expected}. "
        f"Cierra sesión en {provider_label} (o usa una ventana privada) "
        "y vuelve a pulsar Continuar."
    )


def build_yahoo_authorization_url(
    state: str,
    login_hint: str | None = None,
) -> str:
    require_yahoo_oauth_config()
    query: dict[str, str] = {
        "client_id": settings.yahoo_client_id,
        "redirect_uri": settings.yahoo_redirect_uri,
        "response_type": "code",
        "scope": yahoo_authorize_scopes(yahoo_intent_from_state(state)),
        "state": state,
        "nonce": state,
        "language": "es-mx",
    }
    hint = sanitize_login_hint(login_hint)
    if hint:
        query["login_hint"] = hint
    return f"{YAHOO_AUTHORIZE_URL}?{urlencode(query)}"


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
