"""User-initiated case state changes (hecho / posponer / reabrir).

Why this exists next to ``PATCH /cases/{id}``:
``HMS_DATA_MUTATIONS_ENABLED=false`` keeps HMS in *containment* (Sprint 4.8):
automated writers (classifier v1 ``/cases/process``, legacy Gmail sync jobs,
AI analysis) stay locked while historical data is validated. The generic
PATCH can rewrite any case field (summary, priority, owner, due date), so it
stays behind that lock.

These actions are the narrow, per-user exception — the same reasoning that
lets the authenticated guided import write: they run only for the signed-in,
verified user, only touch a case that belongs to *their* mailbox account,
only change the user's own follow-up state (status / resolved_at /
waiting_on / metadata.snoozed_until), and never delete or send mail.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from fastapi import HTTPException

from app.security.identity import require_google_account
from app.services.event_engine import create_case_event
from app.services.oauth_storage import OAuthStorage


UserCaseAction = Literal["done", "reopen", "snooze", "unsnooze"]

USER_ACTIONS: tuple[str, ...] = ("done", "reopen", "snooze", "unsnooze")
MAX_SNOOZE = timedelta(days=90)
# Fields a user action may ever write. Anything else is a programming error.
ALLOWED_FIELDS = frozenset({"status", "resolved_at", "waiting_on", "metadata"})
_CLOSED = {"resolved", "closed", "archived"}
_REOPEN_OK = {"new", "in_progress", "delegated", "waiting_internal", "waiting_external"}

_TITLES = {
    "done": "Marcado como hecho por el usuario",
    "reopen": "Reabierto por el usuario",
    "snooze": "Pospuesto por el usuario",
    "unsnooze": "Recordatorio quitado por el usuario",
}


def _bad_request(message: str) -> HTTPException:
    return HTTPException(
        status_code=400,
        detail={"status": "invalid_case_action", "message": message},
    )


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def build_user_action_patch(
    action: str,
    current: dict[str, Any],
    *,
    now: datetime,
    until: datetime | None = None,
) -> dict[str, Any]:
    """Pure: the exact row change for one user action (no I/O)."""
    if action not in USER_ACTIONS:
        raise _bad_request("Acción no permitida.")

    metadata = dict(current.get("metadata") or {})
    status = str(current.get("status") or "new")
    patch: dict[str, Any] = {}

    if action == "done":
        if status not in _CLOSED:
            metadata["status_before_done"] = status
        metadata.pop("snoozed_until", None)
        patch = {
            "status": "resolved",
            "resolved_at": now.isoformat(),
            "waiting_on": "none",
            "metadata": metadata,
        }
    elif action == "reopen":
        previous = str(metadata.pop("status_before_done", "") or "")
        patch = {
            "status": previous if previous in _REOPEN_OK else "in_progress",
            "resolved_at": None,
            "metadata": metadata,
        }
    elif action == "snooze":
        if until is None:
            raise _bad_request("Indica hasta cuándo posponer.")
        target = _aware(until)
        if target <= now:
            raise _bad_request("La fecha para recordarte ya pasó.")
        if target - now > MAX_SNOOZE:
            raise _bad_request("Solo puedes posponer hasta 90 días.")
        metadata["snoozed_until"] = target.astimezone(timezone.utc).isoformat()
        patch = {"metadata": metadata}
    else:  # unsnooze
        metadata.pop("snoozed_until", None)
        patch = {"metadata": metadata}

    if not set(patch) <= ALLOWED_FIELDS:  # pragma: no cover - defensive
        raise RuntimeError("user action tried to write a non allow-listed field")
    return patch


def apply_user_action(
    *,
    case_id: str,
    action: str,
    until: datetime | None = None,
) -> dict[str, Any]:
    """Apply one action to a case owned by the signed-in user's mailbox."""
    context, account = require_google_account()
    account_id = str(account["id"])
    client = OAuthStorage().client

    rows = (
        client.table("intelligent_cases")
        .select("*")
        .eq("account_id", account_id)
        .eq("id", case_id)
        .limit(1)
        .execute()
    )
    data = getattr(rows, "data", None) or []
    current = data[0] if isinstance(data, list) and data else None
    if not current:
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "message": "Caso no encontrado."},
        )

    now = datetime.now(timezone.utc)
    patch = build_user_action_patch(action, current, now=now, until=until)

    updated = (
        client.table("intelligent_cases")
        .update(patch)
        .eq("id", case_id)
        .eq("account_id", account_id)
        .execute()
    )
    updated_rows = getattr(updated, "data", None) or []
    row = updated_rows[0] if isinstance(updated_rows, list) and updated_rows else {**current, **patch}

    create_case_event(
        client=client,
        workspace_id=str(account["workspace_id"]),
        case_id=case_id,
        event_type="case_user_action",
        level=2 if action == "done" else 1,
        title=_TITLES[action],
        description=None,
        actor_type="user",
        actor_identifier=getattr(context.user, "email", None),
        dedupe_key=None,
        metadata={
            "action": action,
            "previous_status": current.get("status"),
            "snoozed_until": patch.get("metadata", {}).get("snoozed_until"),
        },
    )
    return row
