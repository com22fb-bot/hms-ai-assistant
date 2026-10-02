"""Pure rules for a failed mailbox import (no database access).

Used by the guided import status so a permission failure ("invalid_grant")
explains itself and stops blocking once the user reconnects the mailbox.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


_AUTH_ERROR_TOKENS = (
    "invalid_grant",
    "expired or revoked",
    "token has been expired",
    "invalid_client",
    "unauthorized_client",
    "insufficient authentication",
    "invalid credentials",
    "authenticationfailed",
    "authentication failed",
    "vuelve a conectar",
    "reconnect",
)


def failure_reason(last_error: Any) -> str:
    """"auth" when the mailbox permission expired/was revoked, else "error"."""
    text = str(last_error or "").lower()
    if any(token in text for token in _AUTH_ERROR_TOKENS):
        return "auth"
    return "error"


def _parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def failure_superseded(
    job: dict[str, Any] | None,
    account: dict[str, Any],
) -> bool:
    """A permission failure stops counting once the mailbox was reconnected.

    Reconnecting (OAuth callback / app password) rewrites the account row, so
    an ``updated_at`` newer than the failure means fresh credentials exist and
    the old "invalid_grant" job must not keep the import screen in "failed".
    """
    if not job or job.get("status") != "failed":
        return False
    if failure_reason(job.get("last_error")) != "auth":
        return False
    failed_at = _parse_ts(
        job.get("completed_at") or job.get("updated_at") or job.get("created_at")
    )
    reconnected_at = _parse_ts(account.get("updated_at"))
    return bool(failed_at and reconnected_at and reconnected_at > failed_at)


def failure_message(reason: str) -> str:
    if reason == "auth":
        return (
            "El permiso para leer tu correo venció o fue revocado. "
            "Vuelve a conectar tu buzón y después toca Reintentar."
        )
    return (
        "La descarga se detuvo por un error temporal. "
        "Toca Reintentar para continuar con el correo nuevo."
    )
