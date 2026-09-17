"""Safe cleanup for legacy OAuth Donexto verification flags."""

from __future__ import annotations

from typing import Any

from app.security.donexto_verified import (
    read_donexto_verified,
    user_has_oauth_identity,
)


def _value(user: Any, key: str, default: Any = None) -> Any:
    if isinstance(user, dict):
        return user.get(key, default)
    return getattr(user, key, default)


def _metadata(user: Any, key: str) -> dict[str, Any]:
    value = _value(user, key, {})
    return value if isinstance(value, dict) else {}


def is_legacy_oauth_verified_user(user: Any) -> bool:
    """Identify an OAuth account carrying the old automatic verification flag.

    A recorded email source is authoritative and is never removed by this
    cleanup, even when the account also has an OAuth identity.
    """
    app_metadata = _metadata(user, "app_metadata")
    if not read_donexto_verified(app_metadata):
        return False
    if app_metadata.get("donexto_verification_source") == "email":
        return False
    return user_has_oauth_identity(
        identities=_value(user, "identities"),
        user_metadata=_metadata(user, "user_metadata"),
        app_metadata=app_metadata,
    )


def clear_legacy_oauth_verification(client: Any, user: Any) -> bool:
    """Clear only the legacy Donexto fields for one contaminated user."""
    if not is_legacy_oauth_verified_user(user):
        return False

    app_metadata = _metadata(user, "app_metadata")
    cleaned = {
        key: value
        for key, value in app_metadata.items()
        if key not in {
            "donexto_verified",
            "donexto_verified_at",
            "donexto_verification_source",
        }
    }
    user_id = str(_value(user, "id", "") or "").strip()
    if not user_id:
        raise ValueError("El usuario OAuth no tiene id; no se puede limpiar.")
    client.auth.admin.update_user_by_id(user_id, {"app_metadata": cleaned})
    return True
