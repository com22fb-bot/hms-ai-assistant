"""Attach on-the-fly mail insights to API payloads (read-only).

Insights are computed from the stored ``body_text`` / ``body_html`` on every
read: no column, no migration, no write. Older imports (stored before the
HTML→text fix) benefit too, because ``clean_email`` falls back to the stored
HTML when ``body_text`` is only the subject.
"""

from __future__ import annotations

from typing import Any

from app.services.case_policy import grouped_main_idea
from app.services.mail_insights import safe_insight

_MESSAGE_COLUMNS = "id,subject,sender,body_text,body_html,snippet,triage_category,direction"
_CHUNK = 50


def _rows(response: Any) -> list[dict[str, Any]]:
    data = getattr(response, "data", None)
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    return []


def insights_for_message_ids(client: Any, account_id: str, message_ids: list[str]) -> dict[str, dict[str, Any]]:
    ids = [item for item in dict.fromkeys(str(value) for value in message_ids if value)]
    result: dict[str, dict[str, Any]] = {}
    for start in range(0, len(ids), _CHUNK):
        chunk = ids[start:start + _CHUNK]
        rows = _rows(
            client.table("communication_messages")
            .select(_MESSAGE_COLUMNS)
            .eq("account_id", account_id)
            .in_("id", chunk)
            .execute()
        )
        for row in rows:
            insight = safe_insight(row)
            if insight:
                result[str(row["id"])] = insight
    return result


def attach_thread_insights(client: Any, account_id: str, threads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    try:
        insights = insights_for_message_ids(
            client, account_id, [str(row.get("latest_message_id") or "") for row in threads]
        )
    except Exception:
        return threads
    out: list[dict[str, Any]] = []
    for row in threads:
        insight = insights.get(str(row.get("latest_message_id") or ""))
        if insight:
            row = {**row, "insight": insight, "summary": insight.get("preview") or row.get("summary")}
        out.append(row)
    return out


def _grouped(case: dict[str, Any]) -> dict[str, Any] | None:
    metadata = case.get("metadata")
    if isinstance(metadata, dict) and metadata.get("group_key"):
        return metadata
    return None


def attach_case_insights(client: Any, account_id: str, cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Insight of the case's message: the primary one, or for grouped cases
    (case_policy ``group_key``) the LATEST one plus "N times, last on …"."""
    case_ids = [str(case.get("id")) for case in cases if case.get("id")]
    if not case_ids:
        return cases
    grouped_ids = {str(case.get("id")) for case in cases if _grouped(case)}
    try:
        links: list[dict[str, Any]] = []
        for start in range(0, len(case_ids), _CHUNK):
            links.extend(
                _rows(
                    client.table("case_messages")
                    .select("case_id,message_id,is_primary,linked_at")
                    .in_("case_id", case_ids[start:start + _CHUNK])
                    .execute()
                )
            )
        primary: dict[str, str] = {}
        for link in sorted(
            links,
            key=lambda item: (not bool(item.get("is_primary")), str(item.get("linked_at") or "")),
        ):
            if str(link.get("case_id")) not in grouped_ids:
                primary.setdefault(str(link.get("case_id")), str(link.get("message_id")))
        for link in sorted(links, key=lambda item: str(item.get("linked_at") or ""), reverse=True):
            if str(link.get("case_id")) in grouped_ids:
                primary.setdefault(str(link.get("case_id")), str(link.get("message_id")))
        insights = insights_for_message_ids(client, account_id, list(primary.values()))
    except Exception:
        return cases
    out: list[dict[str, Any]] = []
    for case in cases:
        insight = insights.get(primary.get(str(case.get("id")), ""))
        if not insight:
            out.append(case)
            continue
        metadata = _grouped(case)
        if metadata:
            try:
                insight = {
                    **insight,
                    "main_idea": grouped_main_idea(insight.get("main_idea") or {}, metadata, insight.get("facts") or {}),
                    "occurrences": int(metadata.get("occurrences") or 1),
                    "last_seen_at": metadata.get("last_seen_at"),
                }
            except Exception:  # pragma: no cover - never break the endpoint
                pass
        out.append({**case, "insight": insight})
    return out
