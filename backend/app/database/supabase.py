from __future__ import annotations

import base64
import json
import logging
from typing import Any

from fastapi import HTTPException
from supabase import Client, create_client
from supabase.lib.client_options import SyncClientOptions

from app.core.config import settings


logger = logging.getLogger(__name__)

_USED_ADMIN_KEY_MESSAGE = (
    "SUPABASE_SECRET_KEY no puede usar la API admin de Auth. "
    "En Railway debe ser la clave secret (sb_secret_…) o el JWT legacy service_role. "
    "No uses la clave publishable ni el JWT anon."
)


def validate_supabase_environment() -> None:
    """Verifica que las variables necesarias de Supabase existan."""
    missing_variables: list[str] = []

    if not settings.supabase_url:
        missing_variables.append("SUPABASE_URL")

    if not settings.supabase_secret_key:
        missing_variables.append("SUPABASE_SECRET_KEY")

    if missing_variables:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": (
                    "Faltan variables de Supabase "
                    "en el entorno."
                ),
                "missing_variables": missing_variables,
            },
        )


def admin_key_block_reason(secret_key: str) -> str | None:
    """Return why this key cannot call GoTrue admin, or None if it can.

    ``sb_secret_…`` is accepted: the hosted gateway authorizes it on
    ``/auth/v1/admin/*`` (the verification mail already uses that path).
    The legacy ``service_role`` JWT is also accepted. Publishable keys and
    anon/user JWTs are not.
    """
    token = secret_key.strip()
    if token.startswith("sb_publishable_"):
        return "publishable_key"
    if token.startswith("sb_secret_"):
        return None

    parts = token.split(".")
    if len(parts) != 3:
        return None

    try:
        payload = json.loads(_b64url_json(parts[1]))
    except (ValueError, json.JSONDecodeError):
        return "unreadable_jwt"

    role = payload.get("role") if isinstance(payload, dict) else None
    if role == "service_role":
        return None
    return "jwt_role_not_service"


def reject_non_admin_supabase_key(secret_key: str) -> None:
    """Fail fast when the configured key cannot call Auth admin."""
    reason = admin_key_block_reason(secret_key)
    if reason is None:
        return
    logger.error("supabase_secret_key_cannot_admin reason=%s", reason)
    raise HTTPException(
        status_code=500,
        detail={
            "status": "error",
            "message": _USED_ADMIN_KEY_MESSAGE,
            "reason": reason,
        },
    )


def get_supabase_client() -> Client:
    """Crea un cliente de servicio cuya Admin API no hereda la sesión OTP.

    supabase-py 2.31 comparte un solo dict de headers entre ``auth`` y
    ``auth.admin``. ``verify_otp`` emite ``SIGNED_IN`` y el cliente escribe
    ahí el access token del usuario. El siguiente ``get_user_by_id`` sale
    con ese JWT y GoTrue responde 403 ``User not allowed``.
    """
    validate_supabase_environment()
    reject_non_admin_supabase_key(settings.supabase_secret_key)

    client = create_client(
        settings.supabase_url,
        settings.supabase_secret_key,
        options=SyncClientOptions(
            auto_refresh_token=False,
            persist_session=False,
        ),
    )
    _keep_admin_on_service_key(client)
    return client


def _keep_admin_on_service_key(client: Client) -> None:
    """Pin GoTrue admin headers to the service key, apart from user sessions."""
    key = client.supabase_key
    service_authorization = f"Bearer {key}"
    admin = client.auth.admin
    current = getattr(admin, "_headers", None)
    if isinstance(current, dict):
        admin._headers = {
            **current,
            "apiKey": key,
            "Authorization": service_authorization,
        }

    def _restore(event: str, _session: Any) -> None:
        headers = getattr(admin, "_headers", None)
        if not isinstance(headers, dict):
            return
        if (
            headers.get("Authorization") == service_authorization
            and headers.get("apiKey") == key
        ):
            return
        logger.error("supabase_admin_authorization_reset event=%s", event)
        headers["Authorization"] = service_authorization
        headers["apiKey"] = key

    client.auth.on_auth_state_change(_restore)


def _b64url_json(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)
