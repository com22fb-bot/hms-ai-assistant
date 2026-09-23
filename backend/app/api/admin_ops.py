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
                _best_effort_delete(client, "oauth_credentials", "account_id", account_id)
        for table in _WORKSPACE_CLEANUP_TABLES:
            _best_effort_delete(client, table, "workspace_id", workspace_id)
        _best_effort_delete(client, "communication_accounts", "workspace_id", workspace_id)
        _best_effort_delete(client, "workspace_members", "workspace_id", workspace_id)
        _best_effort_delete(client, "workspaces", "id", workspace_id)

    _best_effort_delete(client, "profiles", "id", user_id)


def _count(client: Any, table: str, **filters: str) -> int:
    try:
        query = client.table(table).select("id", count="exact")
        for column, value in filters.items():
            query = query.eq(column, value)
        response = query.limit(1).execute()
    except Exception:
        logger.info("admin count skip %s", table, exc_info=True)
        return 0
    count = getattr(response, "count", None)
    return int(count or 0)


@router.get("/overview")
def admin_overview() -> dict[str, Any]:
    _require_admin()
    client = get_supabase_client()
    return {
        "status": "ok",
        "counts": {
            "users": _count(client, "profiles"),
            "trials_active": 0,
            "active_paid": 0,
            "mailbox_connected": _count(
                client, "communication_accounts", status="active"
            ),
            "feedback_open": 0,
            "signed_up_no_product_use_24h": 0,
        },
        "product_health": "ok",
        "notes": {
            "account_vs_mailbox": (
                "La cuenta Donexto y el buzón conectado son cosas distintas."
            ),
        },
    }


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
        payload.append(
            {
                "id": user_id,
                "email": email or profile.get("email"),
                "full_name": full_name,
                "is_active": profile.get("is_active", True),
                "created_at": _user_attr(user, "created_at") or profile.get("created_at"),
                "country_code": None,
                "mailbox_connected": user_id in connected,
                "subscription_status": None,
                "plan_code": None,
                "first_product_use_at": None,
                "protected": protected,
            }
        )
    return {"users": payload, "total": len(payload)}


@router.delete("/users/{user_id}")
def admin_delete_user(user_id: str) -> dict[str, Any]:
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

    cleanup_user_records(client, found_id)
    try:
        client.auth.admin.delete_user(found_id)
    except TypeError:
        client.auth.admin.delete_user(found_id, should_soft_delete=False)
    return {
        "status": "deleted",
        "id": found_id,
        "email": email,
    }


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
    _require_admin()
    client = get_supabase_client()
    database_ok = True
    detail = ""
    try:
        client.table("profiles").select("id").limit(1).execute()
    except Exception as error:
        database_ok = False
        detail = type(error).__name__
    allow = admin_allowlist()
    return {
        "status": "ok" if database_ok else "degraded",
        "version": settings.app_version,
        "deploy_marker": os.getenv("HMS_DEPLOY_MARKER", ""),
        "database": {"ok": database_ok, "detail": detail or None},
        "process": {"source": "admin"},
        "admin_configured": bool(allow),
        "admin_allowlist_count": len(allow),
    }
