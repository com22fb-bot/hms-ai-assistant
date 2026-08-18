from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timezone
from datetime import datetime, timedelta, timezone
from typing import Any

from google.oauth2.credentials import Credentials

from app.services.gmail_full_sync import sync_gmail_page
from app.services.gmail_import_inventory import initial_import_snapshot
from app.services.oauth_storage import OAuthStorage
from app.services.yahoo_imap import YahooImapError
from app.services.yahoo_import import (
    YAHOO_PAGE_SIZE,
    is_yahoo_provider,
    sync_yahoo_page,
    yahoo_incremental_refs,
    yahoo_initial_snapshot,
)
from app.services.safe_case_classifier import classify_pending_messages
from app.services.message_rules_service import apply_active_rules_to_unprocessed_messages
from app.services.message_watch_service import match_watch_rules_for_account
from app.services.push_service import notify_actionable_messages


ACTIVE_STATUSES = {"queued", "running", "interrupted"}
_registry_lock = threading.Lock()
_running_jobs: set[str] = set()


def _enabled() -> bool:
    return os.getenv(
        "HMS_GUIDED_IMPORT_ENABLED",
        "true",
    ).strip().lower() in {"1", "true", "yes", "on"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None = None) -> str:
    current = value or _now()
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc).isoformat()


def _rows(response: Any) -> list[dict[str, Any]]:
    data = getattr(response, "data", None)

    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]

    if isinstance(data, dict):
        return [data]

    return []


def _first(response: Any) -> dict[str, Any] | None:
    rows = _rows(response)
    return rows[0] if rows else None


def _storage() -> OAuthStorage:
    return OAuthStorage()


def _yahoo_secret(account: dict[str, Any]) -> tuple[str, str]:
    email = str(account.get("email") or "").strip()
    stored = _storage().get_credentials(str(account["id"])) or {}
    app_password = str(stored.get("access_token") or "")
    if not email or not app_password:
        raise YahooImapError(
            "Vuelve a conectar Yahoo: falta la contraseña de aplicación."
        )
    return email, app_password


def _job(job_id: str) -> dict[str, Any]:
    row = _first(
        _storage().client.table("gmail_sync_jobs")
        .select("*")
        .eq("id", job_id)
        .limit(1)
        .execute()
    )
    if not row:
        raise RuntimeError("Trabajo de importación no encontrado.")
    return row


def _guided_jobs(account_id: str) -> list[dict[str, Any]]:
    rows = _rows(
        _storage().client.table("gmail_sync_jobs")
        .select("*")
        .eq("account_id", account_id)
        .order("created_at", desc=True)
        .limit(30)
        .execute()
    )
    return [
        row
        for row in rows
        if bool((row.get("metadata") or {}).get("guided_import"))
    ]


def _active_guided_job(account_id: str) -> dict[str, Any] | None:
    return next(
        (
            row
            for row in _guided_jobs(account_id)
            if str(row.get("status")) in ACTIVE_STATUSES
        ),
        None,
    )


def _completed_initial_job(
    account_id: str,
) -> dict[str, Any] | None:
    return next(
        (
            row
            for row in _guided_jobs(account_id)
            if row.get("mode") == "historical"
            and row.get("status") == "completed"
        ),
        None,
    )


def _incremental_query(account: dict[str, Any]) -> str:
    last_sync_at = account.get("last_sync_at")
    before_epoch = int(_now().timestamp())

    if last_sync_at:
        parsed = datetime.fromisoformat(
            str(last_sync_at).replace("Z", "+00:00")
        )
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        after_epoch = max(int(parsed.timestamp()) - 300, 0)
        return (
            f"after:{after_epoch} before:{before_epoch} "
            "-in:spam -in:trash -in:drafts"
        )

    return (
        f"newer_than:7d before:{before_epoch} "
        "-in:spam -in:trash -in:drafts"
    )


def _update_job(
    job_id: str,
    values: dict[str, Any],
) -> dict[str, Any] | None:
    return _first(
        _storage().client.table("gmail_sync_jobs")
        .update(values)
        .eq("id", job_id)
        .execute()
    )


def _merge_classification(
    job: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    metadata = dict(job.get("metadata") or {})
    totals = dict(metadata.get("classification_totals") or {})

    for key, value in (result.get("categories") or {}).items():
        totals[key] = int(totals.get(key) or 0) + int(value or 0)

    metadata["classification_totals"] = totals
    metadata["without_case"] = int(
        metadata.get("without_case") or 0
    ) + int(result.get("without_case") or 0)
    return metadata


def _start_thread(job_id: str) -> bool:
    if not _enabled():
        return False

    with _registry_lock:
        if job_id in _running_jobs:
            return False
        _running_jobs.add(job_id)

    thread = threading.Thread(
        target=_run_job,
        args=(job_id,),
        name=f"hms-guided-import-{job_id[:8]}",
        daemon=True,
    )
    thread.start()
    return True


def _run_job(job_id: str) -> None:
    try:
        _update_job(
            job_id,
            {
                "status": "running",
                "started_at": _iso(),
                "heartbeat_at": _iso(),
                "last_error": None,
            },
        )

        while True:
            job = _job(job_id)

            from app.api.auth import (
                get_google_credentials_for_account,
            )

            account_id = str(job["account_id"])
            workspace_id = str(job["workspace_id"])
            account = _storage().get_account(account_id)
            if not account:
                raise RuntimeError("La cuenta de importación ya no existe.")

            if is_yahoo_provider(account):
                metadata = dict(job.get("metadata") or {})
                refs = [
                    str(item)
                    for item in (metadata.get("yahoo_refs") or [])
                    if item
                ]
                offset = int(job.get("next_page_token") or 0)
                secret = _storage().get_credentials(account_id) or {}
                app_password = str(secret.get("access_token") or "")
                if not app_password:
                    raise YahooImapError(
                        "Vuelve a conectar Yahoo: falta la contraseña "
                        "de aplicación."
                    )
                sync_page = sync_yahoo_page(
                    account=account,
                    app_password=app_password,
                    refs=refs,
                    offset=offset,
                    batch_size=int(job.get("batch_size") or YAHOO_PAGE_SIZE),
                )
            else:
                credentials = get_google_credentials_for_account(
                    account_id,
                    expected_workspace_id=workspace_id,
                )
                sync_page = sync_gmail_page(
                    credentials=credentials,
                    batch_size=int(job.get("batch_size") or 100),
                    page_token=job.get("next_page_token"),
                    query=job.get("query"),
                    account_id=account_id,
                )

            current = _job(job_id)
            _update_job(
                job_id,
                {
                    "status": "running",
                    "next_page_token": sync_page.get(
                        "next_page_token"
                    ),
                    "pages_completed": int(
                        current.get("pages_completed") or 0
                    ) + 1,
                    "messages_found": int(
                        current.get("messages_found") or 0
                    ) + int(sync_page.get("page_found") or 0),
                    "messages_inserted": int(
                        current.get("messages_inserted") or 0
                    ) + int(sync_page.get("inserted") or 0),
                    "duplicates": int(
                        current.get("duplicates") or 0
                    ) + int(sync_page.get("duplicates") or 0),
                    "errors": int(current.get("errors") or 0)
                    + int(sync_page.get("errors") or 0),
                    "heartbeat_at": _iso(),
                    "last_error": None,
                },
            )

            inserted_message_ids = [
                str(value)
                for value in (sync_page.get("inserted_message_ids") or [])
                if value
            ]
            if inserted_message_ids:
                apply_active_rules_to_unprocessed_messages(
                    account_id=account_id,
                    workspace_id=workspace_id,
                    limit=len(inserted_message_ids),
                    message_ids=inserted_message_ids,
                )
                result = classify_pending_messages(
                    account_id=account_id,
                    workspace_id=workspace_id,
                    limit=len(inserted_message_ids),
                    message_ids=inserted_message_ids,
                )
                match_watch_rules_for_account(account_id=account_id, workspace_id=workspace_id)
                notify_actionable_messages(
                    account_id=account_id,
                    workspace_id=workspace_id,
                    limit=max(len(inserted_message_ids), 1),
                )
                current = _job(job_id)
                _update_job(
                    job_id,
                    {
                        "cases_processed": int(current.get("cases_processed") or 0) + int(result.get("processed") or 0),
                        "created_cases": int(current.get("created_cases") or 0) + int(result.get("created_cases") or 0),
                        "linked_cases": int(current.get("linked_cases") or 0) + int(result.get("linked_cases") or 0),
                        "errors": int(current.get("errors") or 0) + int(result.get("errors") or 0),
                        "metadata": _merge_classification(current, result),
                        "heartbeat_at": _iso(),
                    },
                )

            if not bool(sync_page.get("has_more")):
                completed_at = _now()
                _update_job(
                    job_id,
                    {
                        "status": "completed",
                        "completed_at": _iso(completed_at),
                        "heartbeat_at": _iso(completed_at),
                        "next_page_token": None,
                    },
                )
                (
                    _storage().client.table(
                        "communication_accounts"
                    )
                    .update(
                        {
                            "last_sync_at": _iso(completed_at),
                            "updated_at": _iso(completed_at),
                        }
                    )
                    .eq("id", account_id)
                    .execute()
                )
                return

            time.sleep(0.08)

    except Exception as error:
        try:
            current = _job(job_id)
            retries = int(current.get("retry_count") or 0) + 1
            max_retries = int(current.get("max_retries") or 3)

            if retries <= max_retries:
                _update_job(
                    job_id,
                    {
                        "status": "interrupted",
                        "retry_count": retries,
                        "last_error": str(error)[:4000],
                        "heartbeat_at": _iso(),
                    },
                )
            else:
                _update_job(
                    job_id,
                    {
                        "status": "failed",
                        "retry_count": retries,
                        "last_error": str(error)[:4000],
                        "completed_at": _iso(),
                        "heartbeat_at": _iso(),
                    },
                )
        except Exception:
            pass
    finally:
        with _registry_lock:
            _running_jobs.discard(job_id)


def _resume_if_needed(job: dict[str, Any] | None) -> None:
    if not job:
        return

    job_id = str(job["id"])
    if str(job.get("status")) in ACTIVE_STATUSES:
        _start_thread(job_id)


def get_guided_import_status(
    account: dict[str, Any],
) -> dict[str, Any]:
    account_id = str(account["id"])
    jobs = _guided_jobs(account_id)
    active = next(
        (
            row
            for row in jobs
            if str(row.get("status")) in ACTIVE_STATUSES
        ),
        None,
    )
    latest = jobs[0] if jobs else None
    completed_initial = _completed_initial_job(account_id)

    _resume_if_needed(active)

    initial_complete = completed_initial is not None
    needs_initial = not initial_complete

    phase = "initial_review" if needs_initial else "ready"
    if active:
        phase = "classifying" if (
            int(active.get("messages_inserted") or 0) > 0
            and int(active.get("cases_processed") or 0)
            < int(active.get("messages_inserted") or 0)
        ) else "downloading"
    elif latest and latest.get("status") == "failed":
        phase = "failed"

    job = active or latest
    metadata = dict((job or {}).get("metadata") or {})
    expected = int((job or {}).get("unique_estimate") or 0)
    downloaded = int((job or {}).get("messages_inserted") or 0)
    classified = int((job or {}).get("cases_processed") or 0)

    download_percent = (
        min(round(downloaded * 100 / expected), 100)
        if expected > 0
        else (100 if job and job.get("status") == "completed" else 0)
    )
    classification_percent = (
        min(round(classified * 100 / max(downloaded, 1)), 100)
        if downloaded > 0
        else 0
    )

    return {
        "status": "ok",
        "guided_import_enabled": _enabled(),
        "provider": str(account.get("provider") or "google"),
        "email": account.get("email"),
        "needs_initial_import": needs_initial,
        "initial_import_complete": initial_complete,
        "phase": phase,
        "active": active,
        "latest": latest,
        "progress": {
            "expected": expected,
            "found": int((job or {}).get("messages_found") or 0),
            "downloaded": downloaded,
            "duplicates": int((job or {}).get("duplicates") or 0),
            "classified": classified,
            "created_cases": int(
                (job or {}).get("created_cases") or 0
            ),
            "linked_cases": int(
                (job or {}).get("linked_cases") or 0
            ),
            "without_case": int(
                metadata.get("without_case") or 0
            ),
            "errors": int((job or {}).get("errors") or 0),
            "download_percent": download_percent,
            "classification_percent": classification_percent,
            "categories": dict(
                metadata.get("classification_totals") or {}
            ),
        },
        "message": (
            "La importación inicial está pendiente."
            if needs_initial
            else "La cuenta está lista para descargar correo nuevo."
        ),
    }


def start_guided_import(
    *,
    account: dict[str, Any],
    mode: str,
    credentials: Credentials | None = None,
) -> dict[str, Any]:
    if not _enabled():
        raise ValueError(
            "La importación guiada está deshabilitada en este entorno."
        )

    account_id = str(account["id"])
    workspace_id = str(account["workspace_id"])
    active = _active_guided_job(account_id)

    if active:
        _resume_if_needed(active)
        return {**active, "reused": True}

    completed_initial = _completed_initial_job(account_id)
    now = _now()

    if mode == "initial":
        if completed_initial:
            raise ValueError(
                "La importación inicial ya fue completada."
            )

        if is_yahoo_provider(account):
            email, app_password = _yahoo_secret(account)
            snapshot = yahoo_initial_snapshot(
                email,
                app_password,
                cutoff_at=now,
            )
            query = str(snapshot["query"])
            expected = int(snapshot["eligible_messages"])
            job_mode = "historical"
            metadata = {
                "guided_import": True,
                "guided_mode": "initial",
                "history_days": snapshot["history_days"],
                "period_start_local": snapshot["period_start_local"],
                "period_end_local": snapshot["period_end_local"],
                "timezone": snapshot["timezone"],
                "yahoo_refs": snapshot.get("yahoo_refs") or [],
                "classification_totals": {},
                "without_case": 0,
            }
            selection_categories = ["six_month_history"]
            batch_size = YAHOO_PAGE_SIZE
        else:
            if credentials is None:
                raise ValueError(
                    "Faltan credenciales de Gmail para la importación."
                )
            snapshot = initial_import_snapshot(
                credentials,
                cutoff_at=now,
            )
            query = str(snapshot["query"])
            expected = int(snapshot["eligible_messages"])
            job_mode = "historical"
            metadata = {
                "guided_import": True,
                "guided_mode": "initial",
                "history_days": snapshot["history_days"],
                "period_start_local": snapshot[
                    "period_start_local"
                ],
                "period_end_local": snapshot["period_end_local"],
                "timezone": snapshot["timezone"],
                "classification_totals": {},
                "without_case": 0,
            }
            selection_categories = ["six_month_history"]
            batch_size = 100
    elif mode == "incremental":
        if not completed_initial:
            raise ValueError(
                "Primero debe completarse la importación inicial."
            )

        if is_yahoo_provider(account):
            email, app_password = _yahoo_secret(account)
            since = now - timedelta(days=7)
            last_sync_at = account.get("last_sync_at")
            if last_sync_at:
                parsed = datetime.fromisoformat(
                    str(last_sync_at).replace("Z", "+00:00")
                )
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                since = parsed - timedelta(minutes=5)
            refs = yahoo_incremental_refs(
                email,
                app_password,
                since=since,
            )
            query = f"yahoo:since:{since.date().isoformat()}"
            expected = len(refs)
            job_mode = "incremental"
            metadata = {
                "guided_import": True,
                "guided_mode": "incremental",
                "timezone": "America/Chihuahua",
                "yahoo_refs": refs,
                "classification_totals": {},
                "without_case": 0,
            }
            selection_categories = ["new_messages"]
            batch_size = YAHOO_PAGE_SIZE
        else:
            query = _incremental_query(account)
            expected = 0
            job_mode = "incremental"
            metadata = {
                "guided_import": True,
                "guided_mode": "incremental",
                "timezone": "America/Chihuahua",
                "classification_totals": {},
                "without_case": 0,
            }
            selection_categories = ["new_messages"]
            batch_size = 100
    else:
        raise ValueError("Modo de importación no válido.")

    payload = {
        "workspace_id": workspace_id,
        "account_id": account_id,
        "status": "queued",
        "mode": job_mode,
        "query": query,
        "next_page_token": None,
        "batch_size": batch_size,
        "process_cases": True,
        "max_retries": 3,
        "selection_categories": selection_categories,
        "unique_estimate": expected,
        "import_cutoff_at": _iso(now),
        "metadata": metadata,
    }

    created = _first(
        _storage().client.table("gmail_sync_jobs")
        .insert(payload)
        .execute()
    )

    if not created:
        raise RuntimeError(
            "Supabase no confirmó el trabajo de importación."
        )

    _start_thread(str(created["id"]))
    return {**created, "reused": False}
