from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.guided_import_job_service import start_guided_import
from app.services.message_rules_service import apply_active_rules_to_unprocessed_messages
from app.services.message_watch_service import match_watch_rules_for_account
from app.services.oauth_storage import OAuthStorage
from app.services.push_service import notify_actionable_messages
from app.services.safe_case_classifier import classify_pending_messages

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_started = False


def _enabled() -> bool:
    return os.getenv("HMS_AUTO_SYNC_ENABLED", "false").strip().lower() in {
        "1", "true", "yes", "on"
    }


def _interval() -> int:
    try:
        return max(int(os.getenv("HMS_AUTO_SYNC_INTERVAL_SECONDS", "120")), 60)
    except ValueError:
        return 120


def _rows(response: Any) -> list[dict[str, Any]]:
    data = getattr(response, "data", None)
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def _initial_complete(client: Any, account_id: str) -> bool:
    jobs = _rows(
        client.table("gmail_sync_jobs")
        .select("mode,status,metadata")
        .eq("account_id", account_id)
        .eq("mode", "historical")
        .eq("status", "completed")
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    return any(bool((job.get("metadata") or {}).get("guided_import")) for job in jobs)


STALE_INTERRUPTED_AFTER = timedelta(hours=2)


def _active_job(client: Any, account_id: str) -> bool:
    """Hay un job vivo para la cuenta (el índice único parcial
    uq_gmail_sync_jobs_active_account actúa de candado por cuenta).

    Un incremental ``interrupted`` sin latido desde hace más de 2 h se da por
    caducado: se marca ``cancelled`` (con motivo en metadata) y deja de
    bloquear. Un histórico interrumpido nunca se reanuda solo: sigue
    bloqueando y se registra para revisión humana.
    """
    rows = _rows(
        client.table("gmail_sync_jobs")
        .select("id,status,mode,heartbeat_at,updated_at,metadata")
        .eq("account_id", account_id)
        .in_("status", ["queued", "running", "paused", "interrupted"])
        .limit(5)
        .execute()
    )
    blocking = False
    now = datetime.now(timezone.utc)
    for job in rows:
        if job.get("status") != "interrupted" or not is_stale_interrupted(job, now):
            blocking = True
            continue
        if str(job.get("mode") or "") != "incremental":
            logger.warning(
                "scheduler historico interrumpido requiere revision job=%s",
                str(job.get("id"))[:8],
            )
            blocking = True
            continue
        metadata = dict(job.get("metadata") or {})
        metadata["stale_recovered_at"] = now.isoformat()
        client.table("gmail_sync_jobs").update(
            {"status": "cancelled", "metadata": metadata, "lease_expires_at": None}
        ).eq("id", job["id"]).eq("status", "interrupted").execute()
        logger.info("scheduler job caducado cancelado job=%s", str(job.get("id"))[:8])
    return blocking


def is_stale_interrupted(job: dict[str, Any], now: datetime) -> bool:
    raw = job.get("heartbeat_at") or job.get("updated_at")
    if not raw:
        return True
    try:
        beat = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return True
    if beat.tzinfo is None:
        beat = beat.replace(tzinfo=timezone.utc)
    return now - beat > STALE_INTERRUPTED_AFTER


def _workspaces_with_members(client: Any, workspace_ids: set[str]) -> set[str]:
    if not workspace_ids:
        return set()
    rows = _rows(
        client.table("workspace_members")
        .select("workspace_id")
        .in_("workspace_id", sorted(workspace_ids))
        .eq("status", "active")
        .is_("deleted_at", "null")
        .execute()
    )
    return {str(row.get("workspace_id")) for row in rows if row.get("workspace_id")}


def eligible_accounts(client: Any) -> list[dict[str, Any]]:
    """Solo cuentas Google ``active`` en workspaces con miembros activos.

    Excluye restos de usuarios borrados (workspaces huérfanos), filas
    ``superseded`` y cuentas en ``needs_reauth``.
    """
    accounts = _rows(
        client.table("communication_accounts")
        .select("id,workspace_id,provider,status")
        .eq("provider", "google")
        .eq("status", "active")
        .execute()
    )
    alive = _workspaces_with_members(
        client, {str(a.get("workspace_id")) for a in accounts if a.get("workspace_id")}
    )
    return [a for a in accounts if str(a.get("workspace_id")) in alive]


def is_invalid_grant(error: BaseException) -> bool:
    text = f"{type(error).__name__} {error}".lower()
    return "invalid_grant" in text or "token has been expired or revoked" in text


def mark_needs_reauth(client: Any, account_id: str) -> None:
    """Token revocado o caducado: no reintentar en cada ciclo.

    La app muestra "Reconecta tu correo" con status ``needs_reauth``; el
    callback OAuth vuelve a poner ``active`` al reconectar.
    """
    client.table("communication_accounts").update(
        {"status": "needs_reauth"}
    ).eq("id", account_id).eq("status", "active").execute()


def _recover_recent_unprocessed(*, account_id: str, workspace_id: str) -> None:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    apply_active_rules_to_unprocessed_messages(
        account_id=account_id,
        workspace_id=workspace_id,
        limit=100,
        received_after=cutoff,
    )
    result = classify_pending_messages(
        account_id=account_id,
        workspace_id=workspace_id,
        limit=100,
        received_after=cutoff,
    )
    if int(result.get("processed") or 0) > 0:
        match_watch_rules_for_account(account_id=account_id, workspace_id=workspace_id)
        notify_actionable_messages(account_id=account_id, workspace_id=workspace_id, limit=100)


def _cycle() -> None:
    storage = OAuthStorage()
    client = storage.client
    for account in eligible_accounts(client):
        account_id = str(account.get("id") or "")
        workspace_id = str(account.get("workspace_id") or "")
        if not account_id or not workspace_id:
            continue
        try:
            if not _initial_complete(client, account_id) or _active_job(client, account_id):
                continue
            _recover_recent_unprocessed(account_id=account_id, workspace_id=workspace_id)
            from app.api.auth import get_google_credentials_for_account
            credentials = get_google_credentials_for_account(
                account_id,
                expected_workspace_id=workspace_id,
            )
            full = storage.get_account(account_id) or account
            start_guided_import(credentials=credentials, account=full, mode="incremental")
        except Exception as error:  # noqa: BLE001
            # Sin PII: solo id corto y tipo de error.
            if is_invalid_grant(error):
                mark_needs_reauth(client, account_id)
                logger.warning("scheduler needs_reauth account=%s", account_id[:8])
            else:
                logger.warning(
                    "scheduler error account=%s error=%s",
                    account_id[:8],
                    type(error).__name__,
                )
            continue


def _worker() -> None:
    time.sleep(15)
    while _enabled():
        try:
            _cycle()
        except Exception as error:  # noqa: BLE001
            logger.warning("scheduler ciclo fallo error=%s", type(error).__name__)
        time.sleep(_interval())


def start_automatic_mail_scheduler() -> bool:
    global _started
    if not _enabled():
        return False
    with _lock:
        if _started:
            return False
        _started = True
    threading.Thread(
        target=_worker,
        name="hms-automatic-mail-sync",
        daemon=True,
    ).start()
    return True
