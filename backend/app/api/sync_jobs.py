from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from app.security.mutation_guard import require_data_mutations_enabled
from app.services.gmail_sync_job_service import (
    cancel_sync_job,
    create_sync_job,
    get_active_sync_job,
    get_sync_job,
    list_sync_jobs,
    pause_sync_job,
    resume_sync_job,
)


router = APIRouter(
    prefix="/gmail/sync-jobs",
    tags=["Gmail Durable Sync"],
)


@router.post("")
def create_job(
    batch_size: int = Query(default=50, ge=1, le=100),
    mode: str = Query(default="incremental"),
    query: str | None = Query(default=None),
    process_cases: bool = Query(default=False),
    max_retries: int = Query(default=3, ge=0, le=10),
) -> dict[str, Any]:
    require_data_mutations_enabled("gmail_sync_job_create")
    job = create_sync_job(
        batch_size=batch_size,
        mode=mode,
        query=query,
        process_cases=process_cases,
        max_retries=max_retries,
    )
    return {"status": "ok", "job": job}


@router.get("")
def jobs(
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    rows = list_sync_jobs(limit=limit)
    return {
        "status": "ok",
        "total": len(rows),
        "jobs": rows,
    }


@router.get("/active")
def active_job() -> dict[str, Any]:
    return {
        "status": "ok",
        "job": get_active_sync_job(),
    }


@router.get("/{job_id}")
def job_detail(job_id: str) -> dict[str, Any]:
    return {"status": "ok", "job": get_sync_job(job_id)}


@router.post("/{job_id}/pause")
def pause_job(job_id: str) -> dict[str, Any]:
    return {"status": "ok", "job": pause_sync_job(job_id)}


@router.post("/{job_id}/resume")
def resume_job(job_id: str) -> dict[str, Any]:
    require_data_mutations_enabled("gmail_sync_job_resume")
    return {"status": "ok", "job": resume_sync_job(job_id)}


@router.post("/{job_id}/cancel")
def cancel_job(job_id: str) -> dict[str, Any]:
    return {"status": "ok", "job": cancel_sync_job(job_id)}
