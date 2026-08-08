from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.security.identity import get_request_context_or_none
from app.services.oauth_storage import OAuthStorage


_SECRET_PATTERNS = (
    re.compile(r"(?i)(access[_-]?token\s*[=:]\s*)[^\s,;]+"),
    re.compile(r"(?i)(refresh[_-]?token\s*[=:]\s*)[^\s,;]+"),
    re.compile(r"(?i)(authorization\s*[=:]\s*bearer\s+)[^\s,;]+"),
    re.compile(r"(?i)(client[_-]?secret\s*[=:]\s*)[^\s,;]+"),
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _first_row(response: Any) -> dict[str, Any] | None:
    data = getattr(response, "data", None)

    if isinstance(data, list):
        return data[0] if data else None

    if isinstance(data, dict):
        return data

    return None


def sanitize_technical_detail(value: Any, limit: int = 8000) -> str | None:
    if value is None:
        return None

    text = str(value)

    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(r"\1[REDACTED]", text)

    return text[:limit]


def _incident_code() -> str:
    now = _utc_now()
    return (
        f"INC-{now.strftime('%Y%m%d-%H%M%S')}-"
        f"{uuid4().hex[:8].upper()}"
    )


def record_incident(
    *,
    component: str,
    event_type: str,
    summary: str,
    severity: str = "medium",
    technical_detail: Any = None,
    http_status: int | None = None,
    request_id: str | None = None,
    workspace_id: str | None = None,
    account_id: str | None = None,
    sync_job_id: str | None = None,
    detected_by: str = "system",
    environment: str = "development",
    metadata: dict[str, Any] | None = None,
    status: str = "open",
    resolution: str | None = None,
) -> dict[str, Any] | None:
    """Persiste un incidente sin propagar errores de la propia bitácora."""

    try:
        storage = OAuthStorage()

        if not account_id or not workspace_id:
            context = get_request_context_or_none()
            account = context.google_account if context else None

            if account:
                account_id = account_id or str(account.get("id") or "") or None
                workspace_id = workspace_id or context.workspace_id

        resolved_at = _utc_now() if status == "resolved" else None

        payload = {
            "incident_code": _incident_code(),
            "workspace_id": workspace_id,
            "account_id": account_id,
            "sync_job_id": sync_job_id,
            "occurred_at": _to_iso(_utc_now()),
            "environment": environment,
            "component": component,
            "severity": severity,
            "event_type": event_type,
            "summary": summary,
            "technical_detail": sanitize_technical_detail(
                technical_detail
            ),
            "http_status": http_status,
            "request_id": request_id,
            "detected_by": detected_by,
            "status": status,
            "resolved_at": _to_iso(resolved_at),
            "resolution": resolution,
            "metadata": metadata or {},
        }

        return _first_row(
            storage.client.table("system_incidents")
            .insert(payload)
            .execute()
        )
    except Exception:
        # La bitácora nunca debe provocar una segunda falla en la aplicación.
        return None
