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


def user_from_admin_response(response: Any) -> Any:
    user = getattr(response, "user", None)
    if user is None and isinstance(response, dict):
        user = response.get("user")
    return user


def raw_user_is_trusted_verified(raw_user: Any) -> bool:
    """True when a service-role user record already has trusted app_metadata.

    ``user_metadata`` is ignored. A missing or non-dict ``app_metadata`` is
    unverified. Call this with the admin user, not with client-supplied JSON.
    """
    if raw_user is None:
        return False
    app_metadata = _user_value(raw_user, "app_metadata")
    if not isinstance(app_metadata, dict):
        return False
    identities = _user_value(raw_user, "identities")
    if not isinstance(identities, list):
        identities = None
    user_metadata = _user_value(raw_user, "user_metadata")
    if not isinstance(user_metadata, dict):
        user_metadata = None
    return trusted_donexto_verified(
        app_metadata,
        oauth_identity_present=user_has_oauth_identity(
            identities=identities,
            user_metadata=user_metadata,
            app_metadata=app_metadata,
        ),
    )


def merge_trusted_email_verification(
    previous: dict[str, Any] | None,
    *,
    verified_at: str | None = None,
) -> dict[str, Any]:
    """App_metadata written by ``mark_donexto_verified`` and the backfill script."""
    stamp = verified_at.strip() if isinstance(verified_at, str) else ""
    return {
        **_metadata_dict(previous),
        "donexto_verified": True,
        "donexto_verified_at": stamp or datetime.now(timezone.utc).isoformat(),
        "donexto_verification_source": "email",
    }


def can_mark_donexto_verified(raw_user: Any) -> bool:
    """Only a Supabase-confirmed Donexto email can be marked."""
    return email_is_confirmed(raw_user)


def mark_donexto_verified(user_id: str) -> None:
    client = get_supabase_client()
    response = client.auth.admin.get_user_by_id(user_id)
    user = user_from_admin_response(response)
    previous = _metadata_dict(_user_value(user, "app_metadata"))
    client.auth.admin.update_user_by_id(
        user_id,
        {"app_metadata": merge_trusted_email_verification(previous)},
    )
