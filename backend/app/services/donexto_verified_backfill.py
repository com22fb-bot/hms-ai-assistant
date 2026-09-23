"""One-time backfill of historical Donexto verification into app_metadata.

Live authorization must keep ignoring ``user_metadata.donexto_verified``.
Only this service-role helper may copy that historical flag, and only for a
real email or OAuth account that is not already trusted.
"""

from __future__ import annotations

from typing import Any

from app.security.donexto_verified import (
    merge_trusted_email_verification,
    raw_user_is_trusted_verified,
    user_has_oauth_identity,
)


def _value(user: Any, key: str, default: Any = None) -> Any:
    if isinstance(user, dict):
        return user.get(key, default)
    return getattr(user, key, default)


def _metadata(user: Any, key: str) -> dict[str, Any]:
    value = _value(user, key, {})
    return value if isinstance(value, dict) else {}


def _identities(user: Any) -> list[Any]:
    identities = _value(user, "identities")
    return identities if isinstance(identities, list) else []


def _has_email_identity(identities: list[Any]) -> bool:
    for row in identities:
        provider = row.get("provider") if isinstance(row, dict) else getattr(row, "provider", None)
        if isinstance(provider, str) and provider.strip().lower() == "email":
            return True
    return False


def is_donexto_verified_backfill_candidate(user: Any) -> bool:
    """Historical ownership proof that never landed in trusted app_metadata.

    Requires boolean ``user_metadata.donexto_verified is True`` plus a real
    email/OAuth identity. Already-trusted accounts are not candidates, so a
    second run does not rewrite them and cleanup will not strip the result.
    """
    user_metadata = _metadata(user, "user_metadata")
    if user_metadata.get("donexto_verified") is not True:
        return False

    email = str(_value(user, "email", "") or "").strip().lower()
    if "@" not in email:
        return False

    if raw_user_is_trusted_verified(user):
        return False

    app_metadata = _metadata(user, "app_metadata")
    identities = _identities(user)
    has_oauth = user_has_oauth_identity(
        identities=identities,
        user_metadata=user_metadata,
        app_metadata=app_metadata,
    )
    return has_oauth or _has_email_identity(identities)


def apply_donexto_verified_backfill(client: Any, user: Any) -> bool:
    """Write trusted app_metadata. Returns False when the user is not eligible."""
    if not is_donexto_verified_backfill_candidate(user):
        return False

    user_id = str(_value(user, "id", "") or "").strip()
    if not user_id:
        raise ValueError("La cuenta no tiene id; no se puede migrar la verificación.")

    app_metadata = _metadata(user, "app_metadata")
    user_metadata = _metadata(user, "user_metadata")
    stamp = app_metadata.get("donexto_verified_at") or user_metadata.get(
        "donexto_verified_at"
    )
    verified_at = stamp if isinstance(stamp, str) else None
    merged = merge_trusted_email_verification(app_metadata, verified_at=verified_at)
    client.auth.admin.update_user_by_id(user_id, {"app_metadata": merged})
    return True
