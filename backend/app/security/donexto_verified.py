"""Trusted Donexto email verification (app_metadata only — not user_metadata)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.database.supabase import get_supabase_client

OAUTH_SIGNUP_VIA = frozenset(
    {
        "yahoo_oauth",
        "microsoft_oauth",
        "google_oauth",
        "apple_oauth",
    }
)


def _metadata_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def is_non_email_provider(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    provider = value.strip().lower()
    return bool(provider) and provider != "email"


def user_has_oauth_identity(
    *,
    identities: list[Any] | None = None,
    user_metadata: dict[str, Any] | None = None,
    app_metadata: dict[str, Any] | None = None,
) -> bool:
    """True when identity was proven at an external OAuth provider."""
    for row in identities or []:
        provider = row.get("provider") if isinstance(row, dict) else getattr(row, "provider", None)
        if is_non_email_provider(provider):
            return True

    via = str((user_metadata or {}).get("signup_via") or "").strip().lower()
    if via in OAUTH_SIGNUP_VIA:
        return True

    app_meta = app_metadata or {}
    if is_non_email_provider(app_meta.get("provider")):
        return True

    providers = app_meta.get("providers")
    if isinstance(providers, list) and any(is_non_email_provider(item) for item in providers):
        return True

    return False


def read_donexto_verified(app_metadata: dict[str, Any] | None) -> bool:
    """Authorization must read only app_metadata (service-role writes)."""
    return _metadata_dict(app_metadata).get("donexto_verified") is True


def trusted_donexto_verified(
    app_metadata: dict[str, Any] | None,
    *,
    oauth_identity_present: bool = False,
) -> bool:
    """Return true only for verification trusted by Donexto.

    An OAuth identity never proves Donexto verification. The only valid proof
    for an OAuth account is the email source written by ``mark_donexto_verified``
    after the ``?donexto_verify=1`` flow. Password accounts keep compatibility
    with the historical app_metadata flag.
    """
    metadata = _metadata_dict(app_metadata)
    if metadata.get("donexto_verified") is not True:
        return False
    if oauth_identity_present:
        return metadata.get("donexto_verification_source") == "email"
    return True


def email_is_confirmed(raw_user: Any) -> bool:
    confirmed = _user_value(raw_user, "email_confirmed_at")
    return bool(confirmed)


def _user_value(user: Any, key: str, default: Any = None) -> Any:
    if isinstance(user, dict):
        return user.get(key, default)
    return getattr(user, key, default)


def can_mark_donexto_verified(raw_user: Any) -> bool:
    """Only a Supabase-confirmed Donexto email can be marked."""
    return email_is_confirmed(raw_user)


def mark_donexto_verified(user_id: str) -> None:
    client = get_supabase_client()
    response = client.auth.admin.get_user_by_id(user_id)
    user = getattr(response, "user", None)
    if user is None and isinstance(response, dict):
        user = response.get("user")
    previous = _metadata_dict(_user_value(user, "app_metadata"))
    merged = {
        **previous,
        "donexto_verified": True,
        "donexto_verified_at": datetime.now(timezone.utc).isoformat(),
        "donexto_verification_source": "email",
    }
    client.auth.admin.update_user_by_id(
        user_id,
        {"app_metadata": merged},
    )
