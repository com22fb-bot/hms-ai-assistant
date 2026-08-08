from __future__ import annotations

from collections import Counter
from typing import Any

from app.services.oauth_storage import OAuthStorage
from app.services.safe_case_classifier import classify_pending_messages


BACKUP_SCHEMA = "hms_backup_logistica1_triage_20260804_2155_mx"


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


def _active_account(storage: OAuthStorage) -> dict[str, Any]:
    account = _first(
        storage.client.table("communication_accounts")
        .select("*")
        .eq("provider", "google")
        .eq("is_active", True)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not account:
        raise RuntimeError("No existe una cuenta Google activa para reclasificar.")
    return account


def _delete_case_surface(
    storage: OAuthStorage,
    *,
    account_id: str,
    workspace_id: str,
) -> int:
    client = storage.client
    case_rows = _rows(
        client.table("intelligent_cases")
        .select("id")
        .eq("account_id", account_id)
        .execute()
    )
    case_ids = [str(row["id"]) for row in case_rows if row.get("id")]

    if case_ids:
        for table in (
            "case_notifications",
            "case_events",
            "case_participants",
            "case_messages",
        ):
            client.table(table).delete().in_("case_id", case_ids).execute()

    client.table("intelligent_cases").delete().eq(
        "account_id", account_id
    ).execute()

    client.table("organizational_patterns").delete().eq(
        "workspace_id", workspace_id
    ).execute()

    return len(case_ids)


def _reset_messages(storage: OAuthStorage, account_id: str) -> int:
    client = storage.client
    rows = _rows(
        client.table("communication_messages")
        .select("id")
        .eq("account_id", account_id)
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

    return len(rows)


def _update_job_summary(
    storage: OAuthStorage,
    *,
    account_id: str,
    processed: int,
    created_cases: int,
    linked_cases: int,
    without_case: int,
    errors: int,
    categories: Counter[str],
) -> None:
    client = storage.client
    jobs = _rows(
        client.table("gmail_sync_jobs")
        .select("*")
        .eq("account_id", account_id)
        .eq("mode", "historical")
        .order("created_at", desc=True)
        .limit(10)
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
            "reclassification_version": "logistica1-hotfix-categorias-v1",
            "backup_schema": BACKUP_SCHEMA,
        }
    )

    client.table("gmail_sync_jobs").update(
        {
            "cases_processed": processed,
            "created_cases": created_cases,
            "linked_cases": linked_cases,
            "errors": errors,
            "last_error": None if errors == 0 else "Reclasificación parcial",
            "metadata": metadata,
        }
    ).eq("id", str(job["id"])).execute()


def main() -> None:
    storage = OAuthStorage()
    account = _active_account(storage)
    account_id = str(account["id"])
    workspace_id = str(account["workspace_id"])

    removed_cases = _delete_case_surface(
        storage,
        account_id=account_id,
        workspace_id=workspace_id,
    )
    total_messages = _reset_messages(storage, account_id)

    processed = 0
    created_cases = 0
    linked_cases = 0
    without_case = 0
    errors = 0
    categories: Counter[str] = Counter()

    for _ in range(30):
        result = classify_pending_messages(
            account_id=account_id,
            workspace_id=workspace_id,
            limit=100,
        )

        found = int(result.get("found") or 0)
        if found == 0:
            break

        processed += int(result.get("processed") or 0)
        created_cases += int(result.get("created_cases") or 0)
        linked_cases += int(result.get("linked_cases") or 0)
        without_case += int(result.get("without_case") or 0)
        errors += int(result.get("errors") or 0)
        categories.update(result.get("categories") or {})

        if int(result.get("processed") or 0) == 0:
            raise RuntimeError(
                "La reclasificación no avanzó. Revisa los errores antes de repetirla."
            )

    remaining = len(
        _rows(
            storage.client.table("communication_messages")
            .select("id")
            .eq("account_id", account_id)
            .eq("case_processed", False)
            .execute()
        )
    )

    _update_job_summary(
        storage,
        account_id=account_id,
        processed=processed,
        created_cases=created_cases,
        linked_cases=linked_cases,
        without_case=without_case,
        errors=errors,
        categories=categories,
    )

    print("===== RECLASIFICACIÓN LOGÍSTICA 1 =====")
    print(f"BACKUP_SCHEMA={BACKUP_SCHEMA}")
    print(f"MENSAJES_TOTALES={total_messages}")
    print(f"CASOS_ANTERIORES_ELIMINADOS={removed_cases}")
    print(f"MENSAJES_CLASIFICADOS={processed}")
    print(f"CASOS_NUEVOS={created_cases}")
    print(f"CASOS_RELACIONADOS={linked_cases}")
    print(f"SIN_CASO={without_case}")
    print(f"PENDIENTES={remaining}")
    print(f"ERRORES={errors}")
    for key, value in categories.most_common():
        print(f"CATEGORIA_{key.upper()}={value}")

    if remaining or errors:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
