from __future__ import annotations

import logging
import os
import queue
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from google.oauth2.credentials import Credentials

from app.services.import_categories import clean_exclude, gmail_query_exclusions
from app.services.import_failure import (
    failure_message,
    failure_reason,
    failure_superseded,
)
from app.services.gmail_full_sync import sync_gmail_page
from app.services.gmail_import_inventory import initial_import_snapshot
from app.services.oauth_storage import OAuthStorage
from app.database.supabase import get_supabase_client
from app.services.account_lifecycle import history_days_for_workspace
from app.services.imap_provider import APP_PASSWORD_IMAP_PROVIDERS
from app.services.icloud_imap import (
    IcloudImapError,
    stored_icloud_uses_app_password,
)
from app.services.yahoo_imap import YahooImapError, yahoo_imap_access
from app.services.yahoo_import import (
    YAHOO_PAGE_SIZE,
    is_yahoo_provider,
    sync_yahoo_page,
    yahoo_incremental_refs,
    yahoo_initial_snapshot,
)
from app.services.microsoft_import import (
    MICROSOFT_PAGE_SIZE,
    MicrosoftImportError,
    is_microsoft_provider,
    microsoft_incremental_refs,
    microsoft_initial_snapshot,
    sync_microsoft_page,
)
from app.services.safe_case_classifier import classify_pending_messages
from app.services.message_rules_service import apply_active_rules_to_unprocessed_messages
from app.services.message_watch_service import match_watch_rules_for_account
from app.services.push_service import notify_actionable_messages
from app.core.config import settings


ACTIVE_STATUSES = {"queued", "running", "interrupted"}
_registry_lock = threading.Lock()
_counter_lock = threading.Lock()


class _Cancelled(Exception):
    """El dueño pidió detener la importación."""


def _is_cancelled(job: dict[str, Any] | None) -> bool:
    return bool(job) and (
        str(job.get("status")) == "cancelled" or bool(job.get("cancel_requested"))
    )


def _is_active(job: dict[str, Any] | None) -> bool:
    return bool(job) and str(job.get("status")) in ACTIVE_STATUSES and not _is_cancelled(job)
_running_jobs: set[str] = set()


_import_logger = logging.getLogger(__name__)


def _notify_or_suppress(*, account_id: str, workspace_id: str, candidates: int) -> None:
    """Avisos push de la importación guiada, apagados salvo IMPORT_PUSH_NOTIFICATIONS_ENABLED=true."""
    if not settings.import_push_notifications_enabled:
        _import_logger.info(
            "guided_import push suppressed: candidates=%d account=%s",
            candidates,
            account_id,
        )
        return
    notify_actionable_messages(
        account_id=account_id,
        workspace_id=workspace_id,
        limit=max(candidates, 1),
    )


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


def is_icloud_provider(account: dict[str, Any] | None) -> bool:
    provider = str((account or {}).get("provider") or "").strip().lower()
    return provider in APP_PASSWORD_IMAP_PROVIDERS


def _app_password_provider(account: dict[str, Any]) -> str:
    provider = str((account or {}).get("provider") or "").strip().lower()
    return provider if provider in APP_PASSWORD_IMAP_PROVIDERS else "icloud"


def _icloud_secret(account: dict[str, Any]) -> tuple[str, str]:
    email = str(account.get("email") or "").strip()
    stored = _storage().get_credentials(str(account["id"])) or {}
    secret = str(stored.get("access_token") or "")
    if not email or not secret or not stored_icloud_uses_app_password(stored):
        label = "Gmail" if _app_password_provider(account) == "gmail_imap" else "iCloud"
        raise IcloudImapError(
            f"Vuelve a conectar {label}. Donexto ya no tiene la contraseña de app.",
            code="icloud_credentials_missing",
        )
    return email, secret


def _yahoo_secret(account: dict[str, Any]) -> tuple[str, str, bool]:
    stored = _storage().get_credentials(str(account["id"])) or {}
    return yahoo_imap_access(stored, str(account.get("email") or ""))


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
            if _is_active(row)
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


def _bump(job_id: str, increments: dict[str, int], extra: Any = None) -> None:
    """Suma contadores del job sin pisar los del otro hilo (descarga / identificación)."""
    with _counter_lock:
        current = _job(job_id)
        values: dict[str, Any] = {
            key: int(current.get(key) or 0) + int(value or 0) for key, value in increments.items()
        }
        if callable(extra):
            values.update(extra(current))
        values["heartbeat_at"] = _iso()
        _update_job(job_id, values)


def _classifier_worker(job_id: str, work: "queue.Queue[list[str] | None]", account_id: str, workspace_id: str) -> None:
    """Identificación de casos en paralelo a la descarga (pipeline)."""
    while True:
        ids = work.get()
        try:
            if ids is None:
                return
            if _is_cancelled(_job(job_id)):
                continue
            t0 = time.monotonic()
            apply_active_rules_to_unprocessed_messages(
                account_id=account_id, workspace_id=workspace_id, limit=len(ids), message_ids=ids,
            )
            result = classify_pending_messages(
                account_id=account_id, workspace_id=workspace_id, limit=len(ids), message_ids=ids,
            )
            match_watch_rules_for_account(account_id=account_id, workspace_id=workspace_id)
            _notify_or_suppress(account_id=account_id, workspace_id=workspace_id, candidates=len(ids))
            _bump(
                job_id,
                {
                    "cases_processed": int(result.get("processed") or 0),
                    "created_cases": int(result.get("created_cases") or 0),
                    "linked_cases": int(result.get("linked_cases") or 0),
                    "errors": int(result.get("errors") or 0),
                },
                extra=lambda current: {"metadata": _merge_classification(current, result)},
            )
            _import_logger.warning(
                "guided_import timing phase=identify job=%s n=%d seconds=%.2f",
                job_id[:8], len(ids), time.monotonic() - t0,
            )
        except Exception:
            _import_logger.warning("guided_import identify batch failed job=%s", job_id[:8], exc_info=True)
            try:
                _bump(job_id, {"errors": len(ids or [])})
            except Exception:
                pass
        finally:
            work.task_done()


def _run_job(job_id: str) -> None:
    work: "queue.Queue[list[str] | None]" = queue.Queue()
    classifier: threading.Thread | None = None

    def _finish_classifier(timeout: float | None = None) -> None:
        if classifier is not None and classifier.is_alive():
            work.put(None)
            classifier.join(timeout)

    try:
        if _is_cancelled(_job(job_id)):
            raise _Cancelled()
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
            if _is_cancelled(job):
                raise _Cancelled()

            from app.api.auth import (
                get_google_credentials_for_account,
            )

            account_id = str(job["account_id"])
            workspace_id = str(job["workspace_id"])
            account = _storage().get_account(account_id)
            if not account:
                raise RuntimeError("La cuenta de importación ya no existe.")
            if classifier is None:
                classifier = threading.Thread(
                    target=_classifier_worker,
                    args=(job_id, work, account_id, workspace_id),
                    name=f"hms-guided-identify-{job_id[:8]}",
                    daemon=True,
                )
                classifier.start()
            page_t0 = time.monotonic()

            if is_icloud_provider(account):
                metadata = dict(job.get("metadata") or {})
                refs = [
                    str(item)
                    for item in (metadata.get("icloud_refs") or [])
                    if item
                ]
                offset = int(job.get("next_page_token") or 0)
                _email, app_password = _icloud_secret(account)
                sync_page = sync_yahoo_page(
                    account=account,
                    app_password=app_password,
                    refs=refs,
                    offset=offset,
                    batch_size=int(job.get("batch_size") or YAHOO_PAGE_SIZE),
                    oauth=False,
                    mailbox_provider=_app_password_provider(account),
                    exclude=list((job.get("metadata") or {}).get("exclude") or []),
                )
            elif is_yahoo_provider(account):
                metadata = dict(job.get("metadata") or {})
                refs = [
                    str(item)
                    for item in (metadata.get("yahoo_refs") or [])
                    if item
                ]
                offset = int(job.get("next_page_token") or 0)
                _email, app_password, oauth = _yahoo_secret(account)
                sync_page = sync_yahoo_page(
                    account=account,
                    app_password=app_password,
                    refs=refs,
                    offset=offset,
                    batch_size=int(job.get("batch_size") or YAHOO_PAGE_SIZE),
                    oauth=oauth,
                    exclude=list((job.get("metadata") or {}).get("exclude") or []),
                )
            elif is_microsoft_provider(account):
                metadata = dict(job.get("metadata") or {})
                refs = [
                    str(item)
                    for item in (metadata.get("microsoft_refs") or [])
                    if item
                ]
                offset = int(job.get("next_page_token") or 0)
                sync_page = sync_microsoft_page(
                    account=account,
                    refs=refs,
                    offset=offset,
                    batch_size=int(job.get("batch_size") or MICROSOFT_PAGE_SIZE),
                    exclude=list((job.get("metadata") or {}).get("exclude") or []),
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
                    exclude=list((job.get("metadata") or {}).get("exclude") or []),
                )

            def _page_values(current: dict[str, Any]) -> dict[str, Any]:
                values: dict[str, Any] = {
                    "next_page_token": sync_page.get("next_page_token"),
                    "last_error": None,
                }
                if not _is_cancelled(current):
                    values["status"] = "running"
                return values

            _bump(
                job_id,
                {
                    "pages_completed": 1,
                    "messages_found": int(sync_page.get("page_found") or 0),
                    "messages_inserted": int(sync_page.get("inserted") or 0),
                    "duplicates": int(sync_page.get("duplicates") or 0),
                    "errors": int(sync_page.get("errors") or 0),
                },
                extra=_page_values,
            )
            timing = sync_page.get("timing") or {}
            _import_logger.warning(
                "guided_import timing phase=download job=%s found=%s inserted=%s seconds=%.2f imap_s=%s db_s=%s",
                job_id[:8], sync_page.get("page_found"), sync_page.get("inserted"),
                time.monotonic() - page_t0, timing.get("imap_s"), timing.get("db_s"),
            )

            inserted_message_ids = [
                str(value)
                for value in (sync_page.get("inserted_message_ids") or [])
                if value
            ]
            if inserted_message_ids:
                work.put(inserted_message_ids)

            if not bool(sync_page.get("has_more")):
                _finish_classifier()
                if _is_cancelled(_job(job_id)):
                    raise _Cancelled()
                # Barrido final: lo descargado que quedó sin identificar (p. ej. tras un reinicio).
                try:
                    sweep = classify_pending_messages(
                        account_id=account_id, workspace_id=workspace_id, limit=1000,
                    )
                    if int(sweep.get("processed") or 0):
                        _bump(
                            job_id,
                            {
                                "cases_processed": int(sweep.get("processed") or 0),
                                "created_cases": int(sweep.get("created_cases") or 0),
                                "linked_cases": int(sweep.get("linked_cases") or 0),
                            },
                            extra=lambda current: {"metadata": _merge_classification(current, sweep)},
                        )
                except Exception:
                    _import_logger.warning("guided_import final sweep failed job=%s", job_id[:8], exc_info=True)
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

    except _Cancelled:
        _finish_classifier(timeout=120)
        _update_job(
            job_id,
            {"status": "cancelled", "completed_at": _iso(), "heartbeat_at": _iso()},
        )
        _import_logger.warning("guided_import cancelled job=%s", job_id[:8])
    except Exception as error:
        _finish_classifier(timeout=120)
        try:
            current = _job(job_id)
            retries = int(current.get("retry_count") or 0) + 1
            max_retries = int(current.get("max_retries") or 3)
            # A revoked/expired permission never heals by retrying.
            permanent = failure_reason(error) == "auth"

            if retries <= max_retries and not permanent:
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
    if _is_active(job):
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
            if _is_active(row)
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
    elif (
        latest
        and latest.get("status") == "failed"
        and not failure_superseded(latest, account)
    ):
        phase = "failed"

    failure: dict[str, Any] | None = None
    if phase == "failed" and latest:
        reason = failure_reason(latest.get("last_error"))
        failure = {
            "reason": reason,
            "reconnect_required": reason == "auth",
            "message": failure_message(reason),
        }

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

    found = int((job or {}).get("messages_found") or 0)
    rate_per_min = 0.0
    eta_seconds: int | None = None
    started_raw = (job or {}).get("started_at")
    if active and started_raw:
        try:
            started = datetime.fromisoformat(str(started_raw).replace("Z", "+00:00"))
            elapsed = max((_now() - started).total_seconds(), 1.0)
            rate_per_min = round(found * 60 / elapsed, 1)
            if found > 0 and expected > found:
                eta_seconds = int((expected - found) * elapsed / found)
            elif expected and found >= expected:
                eta_seconds = 0
        except Exception:
            pass

    recent_cases: list[dict[str, Any]] = []
    if job and (active or str(job.get("status")) in {"completed", "cancelled", "failed", "interrupted"}):
        try:
            recent_cases = _rows(
                _storage().client.table("intelligent_cases")
                .select("id,title,priority,created_at")
                .eq("workspace_id", str(account["workspace_id"]))
                .gte("created_at", str(job.get("created_at") or _iso()))
                .order("created_at", desc=True)
                .limit(8)
                .execute()
            )
        except Exception:
            recent_cases = []

    return {
        "status": "ok",
        "guided_import_enabled": _enabled(),
        "job_status": (job or {}).get("status"),
        "last_error": (job or {}).get("last_error"),
        "heartbeat_at": (job or {}).get("heartbeat_at"),
        "server_time": _iso(),
        "recent_cases": recent_cases,
        "provider": str(account.get("provider") or "google"),
        "email": account.get("email"),
        "needs_initial_import": needs_initial,
        "initial_import_complete": initial_complete,
        "phase": phase,
        "failure": failure,
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
            "processed": found,
            "rate_per_min": rate_per_min,
            "eta_seconds": eta_seconds,
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


def cancel_guided_import(account: dict[str, Any]) -> dict[str, Any]:
    """Detiene la importación guiada activa de esta cuenta (solo la del dueño)."""
    account_id = str(account["id"])
    stopped: list[str] = []
    for row in _guided_jobs(account_id):
        if str(row.get("status")) in ACTIVE_STATUSES and not _is_cancelled(row):
            values: dict[str, Any] = {"cancel_requested": True, "heartbeat_at": _iso()}
            with _registry_lock:
                running_here = str(row["id"]) in _running_jobs
            if not running_here:
                # Sin worker vivo en este proceso: se cierra de inmediato.
                values.update({"status": "cancelled", "completed_at": _iso()})
            _update_job(str(row["id"]), values)
            stopped.append(str(row["id"]))
    return {"status": "ok", "cancelled_jobs": stopped}


def start_guided_import(
    *,
    account: dict[str, Any],
    mode: str,
    credentials: Credentials | None = None,
    exclude: list[str] | None = None,
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

        # Ventana por plan: mensual/prueba 90 días, anual 6 meses.
        plan_history_days = history_days_for_workspace(
            get_supabase_client(), workspace_id
        )

        if is_icloud_provider(account):
            email, app_password = _icloud_secret(account)
            snapshot = yahoo_initial_snapshot(
                email,
                app_password,
                cutoff_at=now,
                oauth=False,
                mailbox_provider=_app_password_provider(account),
                history_days=plan_history_days,
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
                "icloud_refs": snapshot.get("yahoo_refs") or [],
                "classification_totals": {},
                "without_case": 0,
            }
            selection_categories = ["six_month_history"]
            batch_size = YAHOO_PAGE_SIZE
        elif is_yahoo_provider(account):
            email, app_password, oauth = _yahoo_secret(account)
            snapshot = yahoo_initial_snapshot(
                email,
                app_password,
                cutoff_at=now,
                oauth=oauth,
                history_days=plan_history_days,
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
        elif is_microsoft_provider(account):
            snapshot = microsoft_initial_snapshot(
                account, cutoff_at=now, history_days=plan_history_days
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
                "microsoft_refs": snapshot.get("microsoft_refs") or [],
                "classification_totals": {},
                "without_case": 0,
            }
            selection_categories = ["six_month_history"]
            batch_size = MICROSOFT_PAGE_SIZE
        else:
            if credentials is None:
                raise ValueError(
                    "Faltan credenciales de Gmail para la importación."
                )
            snapshot = initial_import_snapshot(
                credentials,
                cutoff_at=now,
                history_days=plan_history_days,
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

        if is_icloud_provider(account):
            email, app_password = _icloud_secret(account)
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
                oauth=False,
                mailbox_provider=_app_password_provider(account),
            )
            query = f"{_app_password_provider(account)}:since:{since.date().isoformat()}"
            expected = len(refs)
            job_mode = "incremental"
            metadata = {
                "guided_import": True,
                "guided_mode": "incremental",
                "timezone": "America/Chihuahua",
                "icloud_refs": refs,
                "classification_totals": {},
                "without_case": 0,
            }
            selection_categories = ["new_messages"]
            batch_size = YAHOO_PAGE_SIZE
        elif is_yahoo_provider(account):
            email, app_password, oauth = _yahoo_secret(account)
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
                oauth=oauth,
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
        elif is_microsoft_provider(account):
            since = now - timedelta(days=7)
            last_sync_at = account.get("last_sync_at")
            if last_sync_at:
                parsed = datetime.fromisoformat(
                    str(last_sync_at).replace("Z", "+00:00")
                )
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                since = parsed - timedelta(minutes=5)
            refs = microsoft_incremental_refs(account, since=since)
            query = f"microsoft:since:{since.date().isoformat()}"
            expected = len(refs)
            job_mode = "incremental"
            metadata = {
                "guided_import": True,
                "guided_mode": "incremental",
                "timezone": "America/Chihuahua",
                "microsoft_refs": refs,
                "classification_totals": {},
                "without_case": 0,
            }
            selection_categories = ["new_messages"]
            batch_size = MICROSOFT_PAGE_SIZE
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

    # Importación personalizada: lo excluido no se descarga ni se guarda.
    # Las sincronizaciones posteriores heredan la elección de la inicial.
    if mode == "initial":
        chosen = clean_exclude(exclude)
    else:
        chosen = clean_exclude(
            ((completed_initial or {}).get("metadata") or {}).get("exclude")
        )
    if chosen:
        metadata["exclude"] = chosen
        if (
            not is_icloud_provider(account)
            and not is_yahoo_provider(account)
            and not is_microsoft_provider(account)
        ):
            extra = gmail_query_exclusions(chosen)
            if extra:
                query = f"{query} {extra}".strip()

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
