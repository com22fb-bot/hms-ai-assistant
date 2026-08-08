from __future__ import annotations

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

_lock = threading.Lock()
_started = False


def _enabled() -> bool:
    return os.getenv("HMS_AUTO_SYNC_ENABLED", "true").strip().lower() in {
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


def _active_job(client: Any, account_id: str) -> bool:
    rows = _rows(
        client.table("gmail_sync_jobs")
        .select("id")
        .eq("account_id", account_id)
        .in_("status", ["queued", "running", "interrupted"])
        .limit(1)
        .execute()
    )
    return bool(rows)


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
    accounts = _rows(
        client.table("communication_accounts")
        .select("*")
        .eq("provider", "google")
        .eq("status", "active")
        .execute()
    )
    for account in accounts:
        account_id = str(account.get("id") or "")
        workspace_id = str(account.get("workspace_id") or "")
        if not account_id or not workspace_id:
            continue
        if not _initial_complete(client, account_id) or _active_job(client, account_id):
            continue
        try:
            _recover_recent_unprocessed(account_id=account_id, workspace_id=workspace_id)
            from app.api.auth import get_google_credentials_for_account
            credentials = get_google_credentials_for_account(
                account_id,
                expected_workspace_id=workspace_id,
            )
            start_guided_import(credentials=credentials, account=account, mode="incremental")
        except Exception:
            continue


def _worker() -> None:
    time.sleep(15)
    while _enabled():
        try:
            _cycle()
        except Exception:
            pass
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
