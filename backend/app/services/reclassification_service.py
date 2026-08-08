from __future__ import annotations

import threading
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.security.identity import require_google_account
from app.services.oauth_storage import OAuthStorage
from app.services.safe_case_classifier import (
    CLASSIFIER_VERSION,
    classify_pending_messages,
)


_registry_lock = threading.Lock()
_running_runs: set[str] = set()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _count(response: Any) -> int:
    value = getattr(response, "count", None)
    if value is None:
        return len(_rows(response))
    try:
        return int(value)
    except (TypeError, ValueError):
        return len(_rows(response))


def _storage() -> OAuthStorage:
    return OAuthStorage()


def _run_or_error(run_id: str) -> dict[str, Any]:
    run = _first(
        _storage().client.table("case_reclassification_runs")
        .select("*")
        .eq("id", run_id)
        .limit(1)
        .execute()
    )
    if not run:
        raise RuntimeError("La ejecución de reclasificación no existe.")
    return run


def _update_run(
    run_id: str,
    values: dict[str, Any],
) -> dict[str, Any] | None:
    return _first(
        _storage().client.table("case_reclassification_runs")
        .update(values)
        .eq("id", run_id)
        .execute()
    )


def _chunks(values: list[str], size: int = 200) -> list[list[str]]:
    return [values[index:index + size] for index in range(0, len(values), size)]


def _backup_rows(
    *,
    run_id: str,
    table_name: str,
    rows: list[dict[str, Any]],
) -> None:
    client = _storage().client
    payload = [
        {
            "run_id": run_id,
            "table_name": table_name,
            "source_id": str(row.get("id") or "") or None,
            "row_data": row,
        }
        for row in rows
    ]
    for start in range(0, len(payload), 200):
        client.table("reclassification_backup_rows").insert(
            payload[start:start + 200]
        ).execute()


def _backup_and_reset(
    *,
    run_id: str,
    account_id: str,
    workspace_id: str,
) -> tuple[int, int]:
    client = _storage().client
    cases = _rows(
        client.table("intelligent_cases")
        .select("*")
        .eq("account_id", account_id)
        .execute()
    )
    case_ids = [str(row["id"]) for row in cases if row.get("id")]
    _backup_rows(run_id=run_id, table_name="intelligent_cases", rows=cases)

    for table_name in (
        "case_messages",
        "case_events",
        "case_notifications",
        "case_participants",
    ):
        related: list[dict[str, Any]] = []
        for group in _chunks(case_ids):
            if not group:
                continue
            related.extend(
                _rows(
                    client.table(table_name)
                    .select("*")
                    .in_("case_id", group)
                    .execute()
                )
            )
        _backup_rows(
            run_id=run_id,
            table_name=table_name,
            rows=related,
        )

    patterns = _rows(
        client.table("organizational_patterns")
        .select("*")
        .eq("workspace_id", workspace_id)
        .execute()
    )
    _backup_rows(
        run_id=run_id,
        table_name="organizational_patterns",
        rows=patterns,
    )

    for table_name in (
        "case_notifications",
        "case_events",
        "case_participants",
        "case_messages",
    ):
        for group in _chunks(case_ids):
            if group:
                client.table(table_name).delete().in_(
                    "case_id", group
                ).execute()

    client.table("intelligent_cases").delete().eq(
        "account_id", account_id
    ).execute()
    client.table("organizational_patterns").delete().eq(
        "workspace_id", workspace_id
    ).execute()

    total_messages = _count(
        client.table("communication_messages")
        .select("id", count="exact")
        .eq("account_id", account_id)
        .limit(1)
        .execute()
    )
    client.table("communication_messages").update(
        {
            "case_processed": False,
            "processed_at": None,
            "triage_category": "unreviewed",
            "actionability_score": None,
            "triage_reason": None,
            "triaged_at": None,
        }
    ).eq("account_id", account_id).execute()

    return len(case_ids), total_messages


def _update_sync_summary(
    *,
    account_id: str,
    processed: int,
    created_cases: int,
    linked_cases: int,
    without_case: int,
    errors: int,
    categories: Counter[str],
    run_id: str,
) -> None:
    client = _storage().client
    jobs = _rows(
        client.table("gmail_sync_jobs")
        .select("*")
        .eq("account_id", account_id)
        .eq("mode", "historical")
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    job = next(
        (
            row
            for row in jobs
            if bool((row.get("metadata") or {}).get("guided_import"))
        ),
        None,
    )
    if not job:
        return

    metadata = dict(job.get("metadata") or {})
    metadata.update(
        {
            "classification_totals": dict(categories),
            "without_case": without_case,
            "reclassification_version": CLASSIFIER_VERSION,
            "reclassification_run_id": run_id,
        }
    )
    client.table("gmail_sync_jobs").update(
        {
            "cases_processed": processed,
            "created_cases": created_cases,
            "linked_cases": linked_cases,
            "errors": errors,
            "last_error": None if errors == 0 else "Reclasificación completada con mensajes en revisión",
            "metadata": metadata,
        }
    ).eq("id", str(job["id"])).execute()


def _run_reclassification(run_id: str) -> None:
    try:
        run = _run_or_error(run_id)
        account_id = str(run["account_id"])
        workspace_id = str(run["workspace_id"])
        metadata = dict(run.get("metadata") or {})
        phase = str(metadata.get("phase") or "backup")

        if phase == "backup":
            removed_cases, total_messages = _backup_and_reset(
                run_id=run_id,
                account_id=account_id,
                workspace_id=workspace_id,
            )
            metadata.update(
                {
                    "phase": "classifying",
                    "categories": {},
                    "linked_cases": 0,
                }
            )
            _update_run(
                run_id,
                {
                    "total_messages": total_messages,
                    "removed_cases": removed_cases,
                    "processed_messages": 0,
                    "without_case": 0,
                    "current_batch": 0,
                    "errors": 0,
                    "action_required": 0,
                    "waiting_external": 0,
                    "review": 0,
                    "informational": 0,
                    "automated": 0,
                    "promotional": 0,
                    "processed_cases": 0,
                    "total_cases": 0,
                    "heartbeat_at": _now_iso(),
                    "metadata": metadata,
                },
            )

        while True:
            current = _run_or_error(run_id)
            if bool(current.get("cancel_requested")):
                _update_run(
                    run_id,
                    {
                        "status": "cancelled",
                        "completed_at": _now_iso(),
                        "heartbeat_at": _now_iso(),
                    },
                )
                return

            result = classify_pending_messages(
                account_id=account_id,
                workspace_id=workspace_id,
                limit=100,
            )
            found = int(result.get("found") or 0)
            if found == 0:
                break

            current = _run_or_error(run_id)
            metadata = dict(current.get("metadata") or {})
            category_totals = Counter(metadata.get("categories") or {})
            category_totals.update(result.get("categories") or {})
            linked_cases = int(metadata.get("linked_cases") or 0) + int(
                result.get("linked_cases") or 0
            )
            metadata.update(
                {
                    "phase": "classifying",
                    "categories": dict(category_totals),
                    "linked_cases": linked_cases,
                    "last_errors": result.get("error_details") or [],
                }
            )

            processed_messages = int(
                current.get("processed_messages") or 0
            ) + int(result.get("processed") or 0)
            created_cases = int(current.get("total_cases") or 0) + int(
                result.get("created_cases") or 0
            )
            without_case = int(current.get("without_case") or 0) + int(
                result.get("without_case") or 0
            )
            errors = int(current.get("errors") or 0) + int(
                result.get("errors") or 0
            )

            _update_run(
                run_id,
                {
                    "processed_messages": processed_messages,
                    "total_cases": created_cases,
                    "processed_cases": created_cases + linked_cases,
                    "without_case": without_case,
                    "current_batch": int(current.get("current_batch") or 0) + 1,
                    "errors": errors,
                    "action_required": int(category_totals.get("action_required", 0)),
                    "waiting_external": int(category_totals.get("waiting_external", 0)),
                    "review": int(category_totals.get("review", 0)),
                    "informational": int(category_totals.get("informational", 0)),
                    "automated": int(category_totals.get("automated", 0)),
                    "promotional": int(category_totals.get("promotional", 0)),
                    "heartbeat_at": _now_iso(),
                    "metadata": metadata,
                },
            )

        final = _run_or_error(run_id)
        metadata = dict(final.get("metadata") or {})
        categories = Counter(metadata.get("categories") or {})
        remaining = _count(
            _storage().client.table("communication_messages")
            .select("id", count="exact")
            .eq("account_id", account_id)
            .eq("case_processed", False)
            .limit(1)
            .execute()
        )
        metadata.update(
            {
                "phase": "completed" if remaining == 0 else "failed",
                "remaining": remaining,
            }
        )
        status = "completed" if remaining == 0 else "failed"
        _update_run(
            run_id,
            {
                "status": status,
                "completed_at": _now_iso(),
                "heartbeat_at": _now_iso(),
                "last_error": (
                    None
                    if remaining == 0
                    else f"Quedaron {remaining} mensajes pendientes."
                ),
                "metadata": metadata,
            },
        )
        _update_sync_summary(
            account_id=account_id,
            processed=int(final.get("processed_messages") or 0),
            created_cases=int(final.get("total_cases") or 0),
            linked_cases=int(metadata.get("linked_cases") or 0),
            without_case=int(final.get("without_case") or 0),
            errors=int(final.get("errors") or 0),
            categories=categories,
            run_id=run_id,
        )

    except Exception as error:
        try:
            _update_run(
                run_id,
                {
                    "status": "failed",
                    "last_error": str(error)[:4000],
                    "completed_at": _now_iso(),
                    "heartbeat_at": _now_iso(),
                },
            )
        except Exception:
            pass
    finally:
        with _registry_lock:
            _running_runs.discard(run_id)


def _start_thread(run_id: str) -> bool:
    with _registry_lock:
        if run_id in _running_runs:
            return False
        _running_runs.add(run_id)

    thread = threading.Thread(
        target=_run_reclassification,
        args=(run_id,),
        name=f"hms-reclassification-{run_id[:8]}",
        daemon=True,
    )
    thread.start()
    return True


def _latest_run(account_id: str) -> dict[str, Any] | None:
    return _first(
        _storage().client.table("case_reclassification_runs")
        .select("*")
        .eq("account_id", account_id)
        .order("started_at", desc=True)
        .limit(1)
        .execute()
    )


def get_reclassification_status() -> dict[str, Any]:
    _, account = require_google_account()
    account_id = str(account["id"])
    run = _latest_run(account_id)

    if run and run.get("status") == "running":
        _start_thread(str(run["id"]))

    total = int((run or {}).get("total_messages") or 0)
    processed = int((run or {}).get("processed_messages") or 0)
    percent = min(round(processed * 100 / total), 100) if total else 0

    return {
        "status": "ok",
        "running": bool(run and run.get("status") == "running"),
        "progress_percent": percent,
        "run": run,
    }


def start_reclassification() -> dict[str, Any]:
    context, account = require_google_account()
    if context.membership_role not in {"owner", "admin"}:
        raise HTTPException(
            status_code=403,
            detail={
                "status": "forbidden",
                "message": "Solo un propietario o administrador puede reclasificar todo el correo.",
            },
        )

    account_id = str(account["id"])
    existing = _latest_run(account_id)
    if existing and existing.get("status") == "running":
        _start_thread(str(existing["id"]))
        return {**existing, "reused": True}

    created = _first(
        _storage().client.table("case_reclassification_runs")
        .insert(
            {
                "workspace_id": context.workspace_id,
                "account_id": account_id,
                "status": "running",
                "dry_run": False,
                "initiated_by": context.user.id,
                "classifier_version": CLASSIFIER_VERSION,
                "heartbeat_at": _now_iso(),
                "metadata": {
                    "phase": "backup",
                    "categories": {},
                    "linked_cases": 0,
                },
            }
        )
        .execute()
    )
    if not created:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "reclassification_not_started",
                "message": "Supabase no confirmó la reclasificación.",
            },
        )

    _start_thread(str(created["id"]))
    return {**created, "reused": False}


def resume_reclassification_jobs() -> None:
    runs = _rows(
        _storage().client.table("case_reclassification_runs")
        .select("id")
        .eq("status", "running")
        .execute()
    )
    for run in runs:
        if run.get("id"):
            _start_thread(str(run["id"]))
