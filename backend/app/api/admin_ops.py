"""Panel /admin: lista de cuentas y borrado de usuarios de prueba.

Solo correos en ``ADMIN_EMAILS``. No se puede borrar al propio admin ni a
otro correo de esa lista.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.database.supabase import get_supabase_client
from app.security.identity import require_request_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])

_WORKSPACE_CLEANUP_TABLES = (
    "gmail_sync_jobs",
    "message_watch_matches",
    "message_watch_rules",
    "message_classification_rules",
    "push_delivery_log",
    "push_subscriptions",
    "hms_notifications",
    "reclassification_backup_rows",
    "case_events",
    "case_messages",
    "case_participants",
    "case_notifications",
    "intelligent_cases",
    "organizational_patterns",
    "communication_messages",
    "communication_threads",
    "tasks",
    "reminders",
    "notifications",
    "audit_log",
    "system_incidents",
    "oauth_states",
)


def admin_allowlist() -> set[str]:
    raw = os.getenv("ADMIN_EMAILS", "")
    return {part.strip().lower() for part in raw.split(",") if part.strip() and "@" in part}


def deletion_block_reason(
    *,
    actor_id: str,
    target_id: str,
    target_email: str,
    allowlist: set[str],
) -> str | None:
    """Spanish reason when this delete must be refused. None means allowed."""
    if not target_id or target_id == actor_id:
        return "No puedes borrar tu propia cuenta de administrador."
    email = (target_email or "").strip().lower()
    if email and email in allowlist:
        return "No se puede borrar un correo de ADMIN_EMAILS."
    return None


def _require_admin() -> Any:
    context = require_request_context()
    allow = admin_allowlist()
    email = (context.user.email or "").strip().lower()
    if not allow or email not in allow:
        raise HTTPException(
            status_code=403,
            detail={
                "status": "admin_forbidden",
                "message": (
                    "Tu correo no está en ADMIN_EMAILS. "
                    "Solo esa lista puede abrir el panel."
                ),
            },
        )
    return context


def _rows(response: Any) -> list[dict[str, Any]]:
    data = getattr(response, "data", None)
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def _user_attr(user: Any, key: str) -> Any:
    if isinstance(user, dict):
        return user.get(key)
    return getattr(user, key, None)


def _listed_users(response: Any) -> list[Any]:
    users = getattr(response, "users", None)
    if users is None and isinstance(response, dict):
        users = response.get("users") or []
    if users is None and isinstance(response, list):
        users = response
    if not isinstance(users, list):
        return []
    return users


def _iter_auth_users(client: Any, limit: int) -> list[Any]:
    list_users = client.auth.admin.list_users
    collected: list[Any] = []
    seen: set[str] = set()
    per_page = 200
    for page in range(1, 51):
        if len(collected) >= limit:
            break
        try:
            response = list_users(page=page, per_page=per_page)
        except TypeError:
            response = list_users()
            return _listed_users(response)[:limit]
        batch = _listed_users(response)
        fresh = False
        for user in batch:
            identity = str(_user_attr(user, "id") or _user_attr(user, "email") or "")
            if not identity or identity in seen:
                continue
            seen.add(identity)
            fresh = True
            collected.append(user)
            if len(collected) >= limit:
                break
        if not fresh or len(batch) < per_page:
            break
    return collected


def _best_effort_delete(client: Any, table: str, column: str, value: str) -> None:
    try:
        client.table(table).delete().eq(column, value).execute()
    except Exception:
        logger.info("admin cleanup skip %s.%s", table, column, exc_info=True)


def cleanup_user_records(client: Any, user_id: str) -> None:
    """Remove profile, mailbox and personal workspace rows before Auth delete."""
    memberships = _rows(
        client.table("workspace_members")
        .select("workspace_id,profile_id")
        .eq("profile_id", user_id)
        .execute()
    )
    workspace_ids = {
        str(row.get("workspace_id"))
        for row in memberships
        if row.get("workspace_id")
    }
    for workspace_id in workspace_ids:
        members = _rows(
            client.table("workspace_members")
            .select("profile_id")
            .eq("workspace_id", workspace_id)
            .execute()
        )
        others = [
            row
            for row in members
            if str(row.get("profile_id") or "") != user_id
        ]
        if others:
            try:
                client.table("workspace_members").delete().eq(
                    "workspace_id", workspace_id
                ).eq("profile_id", user_id).execute()
            except Exception:
                logger.info(
                    "admin cleanup skip membership %s", workspace_id, exc_info=True
                )
            continue

        accounts = _rows(
            client.table("communication_accounts")
            .select("id")
            .eq("workspace_id", workspace_id)
            .execute()
        )
        for account in accounts:
            account_id = str(account.get("id") or "")
            if account_id:
                # Primero desactivar: si un borrado posterior falla, la fila no
                # queda "active" en un workspace huérfano (origen de duplicados
                # y de trabajo del sincronizador sobre cuentas muertas).
                try:
                    client.table("communication_accounts").update(
                        {"status": "inactive"}
                    ).eq("id", account_id).execute()
                except Exception:
                    logger.info("admin cleanup skip deactivate", exc_info=False)
                _best_effort_delete(client, "oauth_credentials", "account_id", account_id)
        for table in _WORKSPACE_CLEANUP_TABLES:
            _best_effort_delete(client, table, "workspace_id", workspace_id)
        _best_effort_delete(client, "communication_accounts", "workspace_id", workspace_id)
        _best_effort_delete(client, "workspace_members", "workspace_id", workspace_id)
        _best_effort_delete(client, "workspaces", "id", workspace_id)

    _best_effort_delete(client, "profiles", "id", user_id)


def _count(client: Any, table: str, **filters: str) -> int | None:
    try:
        query = client.table(table).select("id", count="exact")
        for column, value in filters.items():
            query = query.eq(column, value)
        response = query.limit(1).execute()
    except Exception:
        logger.info("admin count skip %s", table, exc_info=True)
        return None  # «Error de consulta», nunca un 0 aparente
    count = getattr(response, "count", None)
    return int(count) if count is not None else None


def _sum_counts(*values: int | None) -> int | None:
    return None if any(v is None for v in values) else sum(values)  # type: ignore[arg-type]


@router.get("/overview")
def admin_overview() -> dict[str, Any]:
    _require_admin()
    client = get_supabase_client()
    return {
        "status": "ok",
        "counts": {
            "users": _count(client, "profiles"),
            "trials_active": None,  # sin fuente de cobros todavía: «Sin datos»
            "active_paid": None,
            "mailbox_connected": _count(
                client, "communication_accounts", status="active"
            ),
            "feedback_open": None,
            "signed_up_no_product_use_24h": None,
            "contact_nuevo": _count(client, "contact_messages", status="nuevo"),
            "contact_unread": _sum_counts(
                _count(client, "contact_messages", status="nuevo"),
                _count(client, "contact_messages", status="borrador listo"),
            ),
        },
        "product_health": None,  # el estado real sale de GET /admin/health
        "notes": {
            "account_vs_mailbox": (
                "La cuenta Donexto y el buzón conectado son cosas distintas."
            ),
        },
    }


def _empty_mail_stats(stats: dict[str, Any]) -> dict[str, Any]:
    """Sin buzones => 0 real; si la consulta falló => None (la UI muestra «Error de consulta»)."""
    if stats.get("__error__"):
        return {"messages_saved": None, "mailboxes": None, "mail_counts_status": "error"}
    return {"messages_saved": 0, "mailboxes": [], "mail_counts_status": "ok"}


def mailbox_stats_by_user(client: Any, ids: list[str]) -> dict[str, Any]:
    """Conteo real de correos guardados por usuario y por buzón (una sola RPC agregada).

    Usuario -> communication_accounts.connected_by_profile_id -> account_id -> communication_messages.
    No usa el correo de login como buzón. Solo devuelve conteos y metadatos del buzón, nunca contenido.
    """
    if not ids:
        return {}
    try:
        response = client.rpc("admin_mailbox_stats", {"p_profile_ids": ids}).execute()
    except Exception:
        logger.info("admin mailbox stats failed", exc_info=True)
        return {"__error__": True}
    data = getattr(response, "data", None)
    if not isinstance(data, list):
        return {"__error__": True}
    wanted = set(ids)
    out: dict[str, Any] = {}
    for row in data:
        if not isinstance(row, dict):
            continue
        profile_id = str(row.get("profile_id") or "")
        if profile_id not in wanted:  # aislamiento: nunca se atribuye a otro usuario
            continue
        entry = out.setdefault(profile_id, {"messages_saved": 0, "mailboxes": [], "mail_counts_status": "ok"})
        count = int(row.get("messages") or 0)
        entry["messages_saved"] += count
        entry["mailboxes"].append({
            "account_id": row.get("account_id"),
            "provider": row.get("provider"),
            "email": row.get("mailbox_email"),
            "status": row.get("status") or "desconocido",
            "last_sync_at": row.get("last_sync_at"),
            "messages": count,
        })
    for entry in out.values():
        entry["mailboxes"].sort(key=lambda m: -m["messages"])
    return out


@router.get("/users")
def admin_list_users(limit: int = 80) -> dict[str, Any]:
    context = _require_admin()
    bounded = max(1, min(int(limit or 80), 200))
    client = get_supabase_client()
    allow = admin_allowlist()
    actor_id = str(context.user.id)
    auth_users = _iter_auth_users(client, bounded)
    ids = [
        str(_user_attr(user, "id") or "")
        for user in auth_users
        if _user_attr(user, "id")
    ]
    profiles: dict[str, dict[str, Any]] = {}
    connected: set[str] = set()
    plans: dict[str, dict[str, Any]] = {}
    mail_stats = mailbox_stats_by_user(client, ids)
    if ids:
        try:
            for row in _rows(
                client.table("profiles")
                .select("id,email,full_name,is_active,created_at")
                .in_("id", ids)
                .execute()
            ):
                profiles[str(row.get("id"))] = row
        except Exception:
            logger.info("admin profiles lookup failed", exc_info=True)
        try:
            for row in _rows(
                client.table("communication_accounts")
                .select("connected_by_profile_id,status")
                .eq("status", "active")
                .in_("connected_by_profile_id", ids)
                .execute()
            ):
                profile_id = str(row.get("connected_by_profile_id") or "")
                if profile_id:
                    connected.add(profile_id)
        except Exception:
            logger.info("admin mailbox lookup failed", exc_info=True)
        try:
            for row in _rows(
                client.table("account_plans").select("*").in_("user_id", ids).execute()
            ):
                plans[str(row.get("user_id"))] = row
        except Exception:
            logger.info("admin plans lookup failed", exc_info=True)

    payload = []
    for user in auth_users:
        user_id = str(_user_attr(user, "id") or "")
        if not user_id:
            continue
        email = str(_user_attr(user, "email") or "").strip().lower()
        profile = profiles.get(user_id) or {}
        metadata = _user_attr(user, "user_metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {}
        full_name = profile.get("full_name") or metadata.get("full_name")
        protected = user_id == actor_id or (email in allow if email else False)
        plan = plans.get(user_id) or {}
        payload.append(
            {
                "id": user_id,
                "email": email or profile.get("email"),
                "full_name": full_name,
                "is_active": profile.get("is_active", True),
                "created_at": _user_attr(user, "created_at") or profile.get("created_at"),
                "country_code": None,
                "mailbox_connected": user_id in connected,
                "subscription_status": plan.get("status"),
                "plan_code": plan.get("plan_code"),
                "is_test": bool(plan.get("is_test")) if plan else False,
                "trial_started_at": plan.get("trial_started_at"),
                "trial_ends_at": plan.get("trial_ends_at"),
                "first_product_use_at": None,
                "protected": protected,
                **mail_stats.get(user_id, _empty_mail_stats(mail_stats)),
            }
        )
    return {"users": payload, "total": len(payload),
            "mail_counts_status": "error" if mail_stats.get("__error__") else "ok"}


@router.delete("/users/{user_id}")
def admin_delete_user(user_id: str, dry_run: bool = False) -> dict[str, Any]:
    context = _require_admin()
    target_id = (user_id or "").strip()
    if not target_id:
        raise HTTPException(
            status_code=400,
            detail={"status": "invalid_user", "message": "Falta el usuario."},
        )
    client = get_supabase_client()
    try:
        response = client.auth.admin.get_user_by_id(target_id)
    except Exception as error:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "user_not_found",
                "message": "Esa cuenta no está en Supabase Auth.",
            },
        ) from error
    user = getattr(response, "user", None)
    if user is None and isinstance(response, dict):
        user = response.get("user")
    email = str(_user_attr(user, "email") or "").strip().lower()
    found_id = str(_user_attr(user, "id") or "")
    if not found_id:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "user_not_found",
                "message": "Esa cuenta no está en Supabase Auth.",
            },
        )
    reason = deletion_block_reason(
        actor_id=str(context.user.id),
        target_id=found_id,
        target_email=email,
        allowlist=admin_allowlist(),
    )
    if reason:
        raise HTTPException(
            status_code=403,
            detail={"status": "delete_forbidden", "message": reason},
        )

    purge = purge_user_everything(client, found_id, dry_run=dry_run)
    return {**purge_response(purge), "id": found_id, "email": email}


def purge_response(purge: dict[str, Any]) -> dict[str, Any]:
    """Estado fiel: solo «deleted» si Storage también terminó; si no, «deleted_storage_pending»."""
    if purge.get("dry_run"):
        status, complete = "dry_run", False
    else:
        storage = purge.get("storage") or {}
        complete = storage.get("status") in ("ok", "sin_archivos")
        status = "deleted" if complete else "deleted_storage_pending"
    return {
        "status": status,
        "complete": complete,
        "mode": purge.get("mode"),
        "rows_total": purge.get("rows_total"),
        "counts": purge.get("counts") or {},
        "backup_counts": purge.get("backup_counts") or {},
        "shared_kept": purge.get("shared_kept"),
        "shared_accounts": purge.get("shared_accounts") or [],
        "storage_queued": purge.get("storage_queued"),
        "storage": purge.get("storage"),
        "message": None if complete or purge.get("dry_run") else
        "Datos borrados; quedan archivos por borrar en Storage. Se reintentará; ver /admin/storage-purge.",
    }


def purge_user_everything(client: Any, user_id: str, dry_run: bool = False) -> dict[str, Any]:
    """Borra TODO lo del usuario en una sola transacción (``admin_purge_user``).

    Fase de pruebas: sin respaldo. La función SQL registra en la bitácora solo
    conteos por tabla. Si la función aún no existe (migración pendiente), usa
    la limpieza anterior por pasos y luego borra en Supabase Auth.
    """
    try:
        response = client.rpc("admin_purge_user", {"p_user": user_id, "p_dry_run": bool(dry_run)}).execute()
    except Exception as error:
        text = str(error)
        if dry_run:
            raise HTTPException(status_code=409, detail={"status": "dry_run_unavailable",
                                "message": "La simulación requiere la migración 20261023_002."}) from error
        if "admin_purge_user" in text and ("does not exist" in text or "PGRST202" in text):
            # Falla cerrada: sin la función v2 no se borra nada (la limpieza por pasos
            # anterior no respetaba buzones compartidos ni Storage).
            logger.warning("admin_purge_user v2 missing; nothing deleted")
            raise HTTPException(status_code=409, detail={
                "status": "migration_pending",
                "message": "Falta la migración 20261023_002 (borrado v2). No se borró nada."}) from error
        logger.warning("admin_purge_user failed", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "status": "delete_failed",
                "message": "No se pudo borrar la cuenta. No se borró nada.",
            },
        ) from error
    data = getattr(response, "data", None)
    if not isinstance(data, dict):
        data = {}
    if data.get("dry_run"):
        return {"mode": "transactional", "dry_run": True, **data}
    storage = drain_storage_queue(client) if data.get("storage_queued") else {"status": "sin_archivos", "requested": 0}
    return {"mode": "transactional", "dry_run": False, **{k: v for k, v in data.items() if k != "storage_paths"},
            "storage": storage}


# El bucket lo fija SQL (public.admin_attachments_bucket() = 'attachments') y viaja en cada fila
# de la cola; el backend no tiene otro nombre ni variable de entorno. Verificado 23-oct-2026:
# storage.buckets está vacío en producción, así que hoy el borrado de archivos reporta
# «bucket_inexistente» en vez de éxito.


def _bucket_exists(client: Any, bucket: str) -> bool:
    try:
        client.storage.get_bucket(bucket)
        return True
    except Exception:
        return False


def process_storage_queue(client: Any, limit: int = 200) -> dict[str, Any]:
    """Borra archivos pendientes de la cola duradera admin_storage_purge_queue.

    Cada lote reclamado se marca hecho o fallido (con espera exponencial y máximo de
    intentos en SQL). Nunca se reporta «ok» si queda algo pendiente o fallido.
    """
    try:
        claimed = _rows(client.rpc("admin_storage_purge_claim", {"p_limit": limit}).execute())
    except Exception as error:
        return {"status": "error", "message": type(error).__name__}
    done, failed = 0, 0
    by_bucket: dict[str, list[dict[str, Any]]] = {}
    for row in claimed:
        by_bucket.setdefault(str(row.get("bucket") or ""), []).append(row)
    missing: list[str] = []
    for bucket, rows in by_bucket.items():
        if not bucket or not _bucket_exists(client, bucket):
            missing.append(bucket or "(vacío)")
            ids = [int(r["id"]) for r in rows]
            try:
                client.rpc("admin_storage_purge_mark", {"p_ids": ids, "p_ok": False, "p_error": "bucket_inexistente"}).execute()
            except Exception:
                logger.warning("storage purge mark failed", exc_info=True)
            failed += len(rows)
            continue
        for start in range(0, len(rows), 100):
            chunk = rows[start:start + 100]
            ids = [int(r["id"]) for r in chunk]
            try:
                client.storage.from_(bucket).remove([str(r["path"]) for r in chunk])
                ok, err = True, None
            except Exception as error:
                ok, err = False, type(error).__name__
                logger.warning("storage purge chunk failed", exc_info=True)
            try:
                client.rpc("admin_storage_purge_mark", {"p_ids": ids, "p_ok": ok, "p_error": err}).execute()
            except Exception:
                logger.warning("storage purge mark failed", exc_info=True)
                ok = False  # sin marca, se reintentará al vencer la espera
            if ok:
                done += len(chunk)
            else:
                failed += len(chunk)
    try:
        queue = client.rpc("admin_storage_purge_status", {}).execute().data
    except Exception:
        queue = None
    pending = (queue or {}).get("pendiente") if isinstance(queue, dict) else None
    lost = (queue or {}).get("fallido") if isinstance(queue, dict) else None
    if failed or pending or lost or queue is None:
        status = "parcial"
    else:
        status = "ok"
    if missing:
        status = "bucket_inexistente"
    return {"status": status, "processed": len(claimed), "deleted": done, "failed": failed,
            "missing_buckets": missing, "queue": queue}


def drain_storage_queue(client: Any, rounds: int = 10, limit: int = 200) -> dict[str, Any]:
    """Procesa lotes hasta vaciar lo reclamable (máx. rounds); el estado final es el del último lote."""
    total_deleted, total_failed, last = 0, 0, {}
    for _ in range(rounds):
        last = process_storage_queue(client, limit)
        total_deleted += last.get("deleted") or 0
        total_failed += last.get("failed") or 0
        if last.get("status") == "error" or (last.get("processed") or 0) < limit:
            break
    return {**last, "deleted": total_deleted, "failed": total_failed}


@router.get("/storage-purge")
def admin_storage_purge_status() -> dict[str, Any]:
    _require_admin()
    try:
        return {"status": "ok", "queue": get_supabase_client().rpc("admin_storage_purge_status", {}).execute().data}
    except Exception as error:
        return {"status": "error", "queue": None, "message": type(error).__name__}


@router.post("/storage-purge/retry")
def admin_storage_purge_retry() -> dict[str, Any]:
    _require_admin()
    return process_storage_queue(get_supabase_client())


@router.get("/mailboxes/{account_id}/timeline")
def admin_mailbox_timeline(account_id: str) -> dict[str, Any]:
    """Bitácora por buzón: conexión, tokens, sincronizaciones, descargas y proceso (sin contenido)."""
    _require_admin()
    try:
        rows = _rows(get_supabase_client().rpc("admin_mailbox_timeline", {"p_account": account_id}).execute())
    except Exception as error:
        return {"status": "error", "events": None, "message": type(error).__name__}
    return {"status": "ok", "events": rows, "timezone_hint": "UTC; la interfaz muestra CDMX"}


@router.get("/billing/summary")
def admin_billing_summary() -> dict[str, Any]:
    _require_admin()
    return {
        "stub": True,
        "note": "Cobros reales llegan con Stripe. Este resumen no mueve dinero.",
        "summary": {
            "customers": 0,
            "subscriptions_active": 0,
            "subscriptions_trialing": 0,
            "events_recorded": 0,
            "charges_cents": 0,
            "deposits_cents": 0,
            "app_expenses_cents": 0,
            "net_cash_cents_stub": 0,
            "currency_default": "mxn",
        },
        "geo_subscribed_stub": [],
    }


@router.get("/feedback")
def admin_list_feedback(limit: int = 80) -> dict[str, Any]:
    _require_admin()
    del limit
    return {"feedback": [], "total": 0}


@router.post("/feedback")
def admin_create_feedback() -> dict[str, Any]:
    _require_admin()
    raise HTTPException(
        status_code=501,
        detail={
            "status": "not_available",
            "message": "El registro de quejas desde el panel todavía no está activo.",
        },
    )


@router.get("/promotions")
def admin_list_promotions(limit: int = 80) -> dict[str, Any]:
    _require_admin()
    del limit
    return {"promotions": [], "total": 0}


@router.post("/promotions")
def admin_create_promotion() -> dict[str, Any]:
    _require_admin()
    raise HTTPException(
        status_code=501,
        detail={
            "status": "not_available",
            "message": "Los cupones desde el panel todavía no están activos.",
        },
    )


@router.get("/health-extended")
def admin_health_extended() -> dict[str, Any]:
    """Compatibilidad: ahora devuelve la evaluación integrada (Railway, Supabase, Cloudflare, respaldo,
    configuración, errores y frescura). Antes solo consultaba Supabase y ocultaba fallas de Railway."""
    _require_admin()
    from app.api.admin_perf import _health_build
    from app.services import health_eval

    evaluation = health_eval.evaluate(_health_build, get_supabase_client)
    db = next((c for c in evaluation["checks"] if c["id"] == "database"), {})
    allow = admin_allowlist()
    return {
        "status": {"VERDE": "ok", "AMARILLO": "degraded", "ROJO": "critical"}[evaluation["overall"]["state"]],
        "overall": evaluation["overall"],
        "version": settings.app_version,
        "deploy_marker": os.getenv("HMS_DEPLOY_MARKER", ""),
        "database": {"ok": db.get("status") == "ok", "detail": None if db.get("status") == "ok" else db.get("evidence")},
        "checks": evaluation["checks"],
        "evaluated_at": evaluation["evaluated_at"],
        "admin_configured": bool(allow),
        "admin_allowlist_count": len(allow),
    }


@router.get("/lifecycle")
def admin_lifecycle() -> dict[str, Any]:
    """Info: cuentas en prueba y suscripciones no renovadas, con días restantes."""
    _require_admin()
    from app.services.account_lifecycle import lifecycle_overview

    client = get_supabase_client()
    overview = lifecycle_overview(client)
    try:
        runs = client.table("account_cleanup_runs").select("*").order(
            "ran_at", desc=True
        ).limit(5).execute()
        overview["recent_runs"] = _rows(runs)
    except Exception:
        overview["recent_runs"] = []
    return overview


@router.post("/lifecycle/remind/{group}")
def admin_lifecycle_remind(group: str) -> dict[str, Any]:
    """Botón del dueño: manda por Resend el recordatorio de suscripción al grupo."""
    _require_admin()
    from app.services.account_lifecycle import send_subscribe_reminders

    if group not in {"trial", "lapsed"}:
        raise HTTPException(
            status_code=400,
            detail={"status": "invalid_group", "message": "Grupo inválido."},
        )
    result = send_subscribe_reminders(get_supabase_client(), group)
    return {"status": "ok", "group": group, **result}

