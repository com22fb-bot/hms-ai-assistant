from __future__ import annotations

import os
import socket
import threading
import time
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from app.core.config import settings
from app.security.mutation_guard import require_data_mutations_enabled
from app.security.identity import get_request_context_or_none, require_google_account
from app.services.case_engine import process_pending_messages
from app.services.gmail_full_sync import sync_gmail_page
from app.services.oauth_storage import OAuthStorage
from app.services.system_incident_service import record_incident


ACTIVE_STATUSES = (
    "queued",
    "running",
    "paused",
    "interrupted",
)
TERMINAL_STATUSES = (
    "completed",
    "failed",
    "cancelled",
)

_registry_lock = threading.Lock()
_running_jobs: set[str] = set()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _rows(response: Any) -> list[dict[str, Any]]:
    data = getattr(response, "data", None)

    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]

    if isinstance(data, dict):
        return [data]

    return []


def _first_row(response: Any) -> dict[str, Any] | None:
    rows = _rows(response)
    return rows[0] if rows else None


def _storage() -> OAuthStorage:
    return OAuthStorage()


def _active_account() -> tuple[OAuthStorage, dict[str, Any]]:
    _, account = require_google_account()
    return _storage(), account


def _job_or_404(job_id: str) -> dict[str, Any]:
    storage = _storage()
    query = (
        storage.client.table("gmail_sync_jobs")
        .select("*")
        .eq("id", job_id)
    )
    request_context = get_request_context_or_none()

    if request_context is not None:
        query = query.eq("workspace_id", request_context.workspace_id)

    job = _first_row(query.limit(1).execute())

    if not job:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "message": "Trabajo de sincronización no encontrado.",
            },
        )

    return job


def get_sync_job(job_id: str) -> dict[str, Any]:
    return _job_or_404(job_id)


def list_sync_jobs(limit: int = 20) -> list[dict[str, Any]]:
    storage, account = _active_account()
    safe_limit = min(max(limit, 1), 100)

    return _rows(
        storage.client.table("gmail_sync_jobs")
        .select("*")
        .eq("account_id", str(account["id"]))
        .order("created_at", desc=True)
        .limit(safe_limit)
        .execute()
    )


def get_active_sync_job() -> dict[str, Any] | None:
    storage, account = _active_account()

    return _first_row(
        storage.client.table("gmail_sync_jobs")
        .select("*")
        .eq("account_id", str(account["id"]))
        .in_("status", list(ACTIVE_STATUSES))
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )


def _effective_query(
    *,
    mode: str,
    requested_query: str | None,
    account: dict[str, Any],
) -> str | None:
    normalized_query = (requested_query or "").strip() or None

    if mode == "custom":
        if not normalized_query:
            raise HTTPException(
                status_code=422,
                detail={
                    "status": "error",
                    "message": (
                        "El modo custom requiere una consulta de Gmail."
                    ),
                },
            )
        return normalized_query

    if normalized_query:
        return normalized_query

    if mode == "historical":
        return None

    last_sync_at = account.get("last_sync_at")

    if last_sync_at:
        try:
            parsed = datetime.fromisoformat(
                str(last_sync_at).replace("Z", "+00:00")
            )
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)

            # Cinco minutos de solapamiento; los duplicados están protegidos
            # por la llave única account_id + external_message_id.
            epoch = max(int(parsed.timestamp()) - 300, 0)
            return f"after:{epoch}"
        except ValueError:
            pass

    # Primera sincronización incremental segura: evita volver a recorrer
    # todo el historial cuando aún no existe last_sync_at.
    return "newer_than:7d"


def create_sync_job(
    *,
    batch_size: int = 50,
    mode: str = "incremental",
    query: str | None = None,
    process_cases: bool = False,
    max_retries: int = 3,
) -> dict[str, Any]:
    require_data_mutations_enabled("gmail_sync_job_create")
    storage, account = _active_account()
    safe_batch = min(max(batch_size, 1), 100)
    safe_retries = min(max(max_retries, 0), 10)

    if mode not in {"historical", "incremental", "custom"}:
        raise HTTPException(
            status_code=422,
            detail={
                "status": "error",
                "message": "Modo de sincronización no válido.",
            },
        )

    existing = get_active_sync_job()

    if existing:
        if existing.get("status") == "interrupted":
            storage.client.table("gmail_sync_jobs").update(
                {
                    "status": "queued",
                    "cancel_requested": False,
                    "last_error": None,
                }
            ).eq("id", str(existing["id"])).execute()
            start_sync_job(str(existing["id"]))
            existing = _job_or_404(str(existing["id"]))

        return {
            **existing,
            "reused": True,
        }

    effective_query = _effective_query(
        mode=mode,
        requested_query=query,
        account=account,
    )

    payload = {
        "workspace_id": str(account["workspace_id"]),
        "account_id": str(account["id"]),
        "status": "queued",
        "mode": mode,
        "query": effective_query,
        "next_page_token": None,
        "batch_size": safe_batch,
        "process_cases": process_cases,
        "max_retries": safe_retries,
        "metadata": {
            "requested_query": query,
            "effective_query": effective_query,
            "created_from": "api",
        },
    }

    try:
        created = _first_row(
            storage.client.table("gmail_sync_jobs")
            .insert(payload)
            .execute()
        )
    except Exception:
        # Protege contra dos clics concurrentes: recupera el trabajo único.
        concurrent = get_active_sync_job()
        if concurrent:
            return {
                **concurrent,
                "reused": True,
            }
        raise

    if not created:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": (
                    "Supabase no confirmó el trabajo de sincronización."
                ),
            },
        )

    start_sync_job(str(created["id"]))
    return {
        **_job_or_404(str(created["id"])),
        "reused": False,
    }


def _update_job(job_id: str, values: dict[str, Any]) -> dict[str, Any] | None:
    return _first_row(
        _storage().client.table("gmail_sync_jobs")
        .update(values)
        .eq("id", job_id)
        .execute()
    )


def _worker_id() -> str:
    return (
        f"{socket.gethostname()}:{os.getpid()}:"
        f"{threading.get_ident()}:{uuid4().hex[:8]}"
    )


def start_sync_job(job_id: str) -> bool:
    if not settings.data_mutations_enabled:
        return False

    with _registry_lock:
        if job_id in _running_jobs:
            return False
        _running_jobs.add(job_id)

    thread = threading.Thread(
        target=_run_sync_job,
        args=(job_id,),
        name=f"gmail-sync-{job_id[:8]}",
        daemon=True,
    )
    thread.start()
    return True


def _run_sync_job(job_id: str) -> None:
    if not settings.data_mutations_enabled:
        return

    worker_id = _worker_id()

    try:
        _update_job(
            job_id,
            {
                "status": "running",
                "worker_id": worker_id,
                "started_at": _to_iso(_utc_now()),
                "heartbeat_at": _to_iso(_utc_now()),
                "last_error": None,
            },
        )

        while True:
            job = _job_or_404(job_id)

            if bool(job.get("cancel_requested")):
                _update_job(
                    job_id,
                    {
                        "status": "cancelled",
                        "completed_at": _to_iso(_utc_now()),
                        "heartbeat_at": _to_iso(_utc_now()),
                        "worker_id": None,
                    },
                )
                return

            if job.get("status") == "paused":
                _update_job(
                    job_id,
                    {
                        "heartbeat_at": _to_iso(_utc_now()),
                        "worker_id": None,
                    },
                )
                return

            try:
                # Importación diferida para evitar un ciclo con el router OAuth.
                from app.api.auth import get_google_credentials_for_account

                account_id = str(job["account_id"])
                credentials = get_google_credentials_for_account(
                    account_id,
                    expected_workspace_id=str(job["workspace_id"]),
                )
                sync_page = sync_gmail_page(
                    credentials=credentials,
                    batch_size=int(job.get("batch_size") or 50),
                    page_token=job.get("next_page_token"),
                    query=job.get("query"),
                    account_id=account_id,
                )

                page_update = {
                    "status": "running",
                    "next_page_token": sync_page.get("next_page_token"),
                    "pages_completed": int(
                        job.get("pages_completed") or 0
                    ) + 1,
                    "messages_found": int(
                        job.get("messages_found") or 0
                    ) + int(sync_page.get("page_found") or 0),
                    "messages_inserted": int(
                        job.get("messages_inserted") or 0
                    ) + int(sync_page.get("inserted") or 0),
                    "duplicates": int(job.get("duplicates") or 0)
                    + int(sync_page.get("duplicates") or 0),
                    "errors": int(job.get("errors") or 0)
                    + int(sync_page.get("errors") or 0),
                    "retry_count": 0,
                    "heartbeat_at": _to_iso(_utc_now()),
                    "last_error": None,
                    "worker_id": worker_id,
                }
                _update_job(job_id, page_update)

                if (
                    bool(job.get("process_cases", False))
                    and int(sync_page.get("inserted") or 0) > 0
                ):
                    case_result = process_pending_messages(
                        limit=int(job.get("batch_size") or 50),
                        account_id=str(job["account_id"]),
                        workspace_id=str(job["workspace_id"]),
                    )
                    refreshed = _job_or_404(job_id)
                    _update_job(
                        job_id,
                        {
                            "cases_processed": int(
                                refreshed.get("cases_processed") or 0
                            ) + int(case_result.get("processed") or 0),
                            "created_cases": int(
                                refreshed.get("created_cases") or 0
                            ) + int(
                                case_result.get("created_cases") or 0
                            ),
                            "linked_cases": int(
                                refreshed.get("linked_cases") or 0
                            ) + int(
                                case_result.get("linked_to_existing") or 0
                            ),
                            "errors": int(refreshed.get("errors") or 0)
                            + int(case_result.get("errors") or 0),
                            "heartbeat_at": _to_iso(_utc_now()),
                        },
                    )

                if not bool(sync_page.get("has_more")):
                    completed_at = _utc_now()
                    _update_job(
                        job_id,
                        {
                            "status": "completed",
                            "completed_at": _to_iso(completed_at),
                            "heartbeat_at": _to_iso(completed_at),
                            "worker_id": None,
                            "lease_expires_at": None,
                            "next_page_token": None,
                        },
                    )

                    if job.get("mode") != "custom":
                        _storage().client.table(
                            "communication_accounts"
                        ).update(
                            {"last_sync_at": _to_iso(completed_at)}
                        ).eq(
                            "id", str(job["account_id"])
                        ).execute()
                    return

                time.sleep(0.05)

            except Exception as error:
                current = _job_or_404(job_id)
                retry_count = int(current.get("retry_count") or 0) + 1
                max_retries = int(current.get("max_retries") or 3)
                is_retryable = retry_count <= max_retries

                _update_job(
                    job_id,
                    {
                        "status": (
                            "running" if is_retryable else "failed"
                        ),
                        "retry_count": retry_count,
                        "errors": int(current.get("errors") or 0) + 1,
                        "last_error": str(error)[:8000],
                        "heartbeat_at": _to_iso(_utc_now()),
                        "completed_at": (
                            None
                            if is_retryable
                            else _to_iso(_utc_now())
                        ),
                        "worker_id": (
                            worker_id if is_retryable else None
                        ),
                    },
                )

                if not is_retryable:
                    record_incident(
                        component="gmail/durable-sync",
                        event_type="gmail_sync_failed",
                        summary=(
                            "La sincronización durable de Gmail agotó "
                            "sus reintentos automáticos."
                        ),
                        severity="high",
                        technical_detail=error,
                        workspace_id=str(current["workspace_id"]),
                        account_id=str(current["account_id"]),
                        sync_job_id=job_id,
                        metadata={
                            "retry_count": retry_count,
                            "max_retries": max_retries,
                            "pages_completed": current.get(
                                "pages_completed"
                            ),
                        },
                    )
                    return

                time.sleep(min(2 ** retry_count, 30))

    except Exception as error:
        try:
            current = _job_or_404(job_id)
            _update_job(
                job_id,
                {
                    "status": "interrupted",
                    "last_error": str(error)[:8000],
                    "heartbeat_at": _to_iso(_utc_now()),
                    "worker_id": None,
                },
            )
            record_incident(
                component="gmail/durable-sync",
                event_type="gmail_sync_interrupted",
                summary=(
                    "El trabajo durable de Gmail fue interrumpido "
                    "fuera del ciclo normal."
                ),
                severity="high",
                technical_detail=error,
                workspace_id=str(current["workspace_id"]),
                account_id=str(current["account_id"]),
                sync_job_id=job_id,
            )
        except Exception:
            pass
    finally:
        with _registry_lock:
            _running_jobs.discard(job_id)


def pause_sync_job(job_id: str) -> dict[str, Any]:
    job = _job_or_404(job_id)

    if job.get("status") in TERMINAL_STATUSES:
        return job

    _update_job(job_id, {"status": "paused"})
    return _job_or_404(job_id)


def resume_sync_job(job_id: str) -> dict[str, Any]:
    require_data_mutations_enabled("gmail_sync_job_resume")
    job = _job_or_404(job_id)

    if job.get("status") in TERMINAL_STATUSES:
        return job

    _update_job(
        job_id,
        {
            "status": "queued",
            "cancel_requested": False,
            "last_error": None,
        },
    )
    start_sync_job(job_id)
    return _job_or_404(job_id)


def cancel_sync_job(job_id: str) -> dict[str, Any]:
    job = _job_or_404(job_id)

    if job.get("status") in TERMINAL_STATUSES:
        return job

    _update_job(job_id, {"cancel_requested": True})
    return _job_or_404(job_id)


def resume_incomplete_jobs() -> int:
    """Reanuda trabajos que quedaron activos antes de reiniciar FastAPI."""

    if not settings.data_mutations_enabled:
        return 0

    try:
        storage = _storage()
        jobs = _rows(
            storage.client.table("gmail_sync_jobs")
            .select("*")
            .in_("status", ["queued", "running", "interrupted"])
            .order("created_at")
            .execute()
        )

        resumed = 0

        for job in jobs:
            job_id = str(job["id"])

            if job.get("status") == "running":
                _update_job(
                    job_id,
                    {
                        "status": "interrupted",
                        "last_error": (
                            "El backend se reinició antes de que el trabajo "
                            "confirmara su finalización."
                        ),
                        "worker_id": None,
                    },
                )

                record_incident(
                    component="gmail/durable-sync",
                    event_type="gmail_sync_recovered_after_restart",
                    summary=(
                        "Se detectó y reanudó una sincronización de Gmail "
                        "interrumpida por el reinicio del backend."
                    ),
                    severity="medium",
                    workspace_id=str(job["workspace_id"]),
                    account_id=str(job["account_id"]),
                    sync_job_id=job_id,
                    status="resolved",
                    resolution=(
                        "El backend recuperó el trabajo desde el último "
                        "next_page_token persistido."
                    ),
                )

            _update_job(
                job_id,
                {
                    "status": "queued",
                    "cancel_requested": False,
                    "worker_id": None,
                },
            )

            if start_sync_job(job_id):
                resumed += 1

        return resumed
    except Exception as error:
        record_incident(
            component="gmail/durable-sync",
            event_type="gmail_sync_resume_scan_failed",
            summary=(
                "No fue posible revisar trabajos pendientes al iniciar "
                "el backend."
            ),
            severity="high",
            technical_detail=error,
        )
        return 0
