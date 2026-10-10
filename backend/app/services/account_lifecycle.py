"""Planes, ventana de importación y limpieza diaria de cuentas.

Reglas (Términos y Privacidad, 9 oct 2026):
- Plan mensual (y prueba): se importan los últimos 90 días de correo.
- Plan anual: los últimos 6 meses (183 días).
- Prueba: la cuenta se conserva 7 días después de que termina la prueba.
- Suscripción no renovada: se conserva 30 días después del vencimiento.
- Después, la limpieza diaria de las 3:00 a. m. (America/Mexico_City) la borra.
- Recordatorios por correo (Resend): a la mitad del plazo y 1 día antes del borrado.

Seguridad:
- El borrado real solo corre con ``ACCOUNT_CLEANUP_DELETE_ENABLED=true``.
  Por defecto la limpieza es *dry-run*: cuenta y registra, no borra.
- Los recordatorios automáticos solo salen con ``ACCOUNT_REMINDERS_AUTO_ENABLED=true``.
  El botón de /admin los manda cuando el dueño lo presiona.
- Nunca se toca una cuenta protegida (hmcelinfo@gmail.com, ADMIN_EMAILS o
  ``ACCOUNT_CLEANUP_PROTECTED_EMAILS``).
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

MEXICO_CITY = ZoneInfo("America/Mexico_City")
MONTHLY_HISTORY_DAYS = 90
ANNUAL_HISTORY_DAYS = 183
TRIAL_GRACE_DAYS = 7
LAPSED_GRACE_DAYS = 30
CLEANUP_HOUR_LOCAL = 3
ALWAYS_PROTECTED = frozenset({"hmcelinfo@gmail.com"})

_lock = threading.Lock()
_started = False


def _flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def deletion_enabled() -> bool:
    return _flag("ACCOUNT_CLEANUP_DELETE_ENABLED")


def auto_reminders_enabled() -> bool:
    return _flag("ACCOUNT_REMINDERS_AUTO_ENABLED")


def protected_emails() -> set[str]:
    raw = ",".join(
        [os.getenv("ADMIN_EMAILS", ""), os.getenv("ACCOUNT_CLEANUP_PROTECTED_EMAILS", "")]
    )
    found = {part.strip().lower() for part in raw.split(",") if part.strip()}
    return found | set(ALWAYS_PROTECTED)


# ------------------------------------------------------------------ ventana
def history_days_for_plan(plan_code: str | None) -> int:
    return ANNUAL_HISTORY_DAYS if (plan_code or "").strip().lower() == "annual" else MONTHLY_HISTORY_DAYS


def _rows(response: Any) -> list[dict[str, Any]]:
    data = getattr(response, "data", None)
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def history_days_for_workspace(client: Any, workspace_id: str) -> int:
    """Días de historial para la importación inicial de un buzón.

    Cuentas protegidas (dueño/pruebas) usan la ventana anual. Si no hay plan
    registrado, se usa la del plan mensual (90 días). Ante un error, 90 días.
    """
    try:
        members = _rows(
            client.table("workspace_members").select("profile_id").eq("workspace_id", workspace_id).execute()
        )
        profile_ids = [str(row["profile_id"]) for row in members if row.get("profile_id")]
        if not profile_ids:
            return MONTHLY_HISTORY_DAYS
        profiles = _rows(client.table("profiles").select("id,email").in_("id", profile_ids).execute())
        if any(str(p.get("email") or "").lower() in protected_emails() for p in profiles):
            return ANNUAL_HISTORY_DAYS
        plans = _rows(
            client.table("account_plans").select("plan_code,status").in_("user_id", profile_ids).execute()
        )
        if any(p.get("plan_code") == "annual" and p.get("status") == "active" for p in plans):
            return ANNUAL_HISTORY_DAYS
    except Exception:
        logger.info("history window lookup failed; using monthly", exc_info=True)
    return MONTHLY_HISTORY_DAYS


# ------------------------------------------------------------------ plazos
def _parse(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class Retention:
    group: str            # "trial" | "lapsed"
    ended_at: datetime    # fin de la prueba o vencimiento
    delete_at: datetime
    midpoint_at: datetime
    final_reminder_at: datetime

    def days_left(self, now: datetime) -> int:
        seconds = (self.delete_at - now).total_seconds()
        return max(0, int((seconds + 86399) // 86400))


def retention_for(plan: dict[str, Any], now: datetime) -> Retention | None:
    """Plazo de conservación de una cuenta, o None si no aplica (activa)."""
    status = str(plan.get("status") or "")
    if status == "trialing" or (plan.get("plan_code") == "trial" and status in {"", "lapsed", "canceled"}):
        ended = _parse(plan.get("trial_ends_at"))
        if not ended or ended > now:
            return None
        group, grace = "trial", TRIAL_GRACE_DAYS
    elif status in {"lapsed", "canceled"}:
        ended = _parse(plan.get("period_ends_at"))
        if not ended or ended > now:
            return None
        group, grace = "lapsed", LAPSED_GRACE_DAYS
    else:
        return None
    delete_at = ended + timedelta(days=grace)
    return Retention(
        group=group,
        ended_at=ended,
        delete_at=delete_at,
        midpoint_at=ended + timedelta(days=grace / 2),
        final_reminder_at=delete_at - timedelta(days=1),
    )


def next_cleanup_at(now: datetime) -> datetime:
    """Próxima corrida a las 3:00 a. m. de Ciudad de México (en UTC)."""
    local = now.astimezone(MEXICO_CITY)
    target = local.replace(hour=CLEANUP_HOUR_LOCAL, minute=0, second=0, microsecond=0)
    if target <= local:
        target = target + timedelta(days=1)
        target = target.replace(hour=CLEANUP_HOUR_LOCAL, minute=0, second=0, microsecond=0)
    return target.astimezone(timezone.utc)


# ------------------------------------------------------------------ listado
def _emails_by_id(client: Any, user_ids: list[str]) -> dict[str, str]:
    if not user_ids:
        return {}
    try:
        rows = _rows(client.table("profiles").select("id,email").in_("id", user_ids).execute())
    except Exception:
        logger.info("profiles lookup failed", exc_info=True)
        return {}
    return {str(r["id"]): str(r.get("email") or "").lower() for r in rows if r.get("id")}


def lifecycle_overview(client: Any, now: datetime | None = None) -> dict[str, Any]:
    """Cuentas en prueba y suscripciones no renovadas, con días restantes."""
    now = now or datetime.now(timezone.utc)
    try:
        plans = _rows(client.table("account_plans").select("*").execute())
    except Exception:
        logger.info("account_plans unavailable", exc_info=True)
        plans = []
    emails = _emails_by_id(client, [str(p["user_id"]) for p in plans if p.get("user_id")])
    protected = protected_emails()
    trials: list[dict[str, Any]] = []
    lapsed: list[dict[str, Any]] = []
    for plan in plans:
        user_id = str(plan.get("user_id") or "")
        email = emails.get(user_id, "")
        row = {
            "user_id": user_id,
            "email": email,
            "plan_code": plan.get("plan_code"),
            "status": plan.get("status"),
            "protected": email in protected,
        }
        retention = retention_for(plan, now)
        if plan.get("status") == "trialing" and retention is None:
            ends = _parse(plan.get("trial_ends_at"))
            trials.append({**row, "phase": "en_prueba", "trial_ends_at": ends.isoformat() if ends else None,
                           "delete_at": (ends + timedelta(days=TRIAL_GRACE_DAYS)).isoformat() if ends else None,
                           "days_left": None if not ends else max(0, (ends + timedelta(days=TRIAL_GRACE_DAYS) - now).days)})
            continue
        if retention is None:
            continue
        entry = {**row, "phase": "por_borrar", "ended_at": retention.ended_at.isoformat(),
                 "delete_at": retention.delete_at.isoformat(), "days_left": retention.days_left(now)}
        (trials if retention.group == "trial" else lapsed).append(entry)
    trials.sort(key=lambda r: (r.get("days_left") is None, r.get("days_left") or 0))
    lapsed.sort(key=lambda r: r.get("days_left") or 0)
    return {
        "trials": trials,
        "lapsed": lapsed,
        "deletion_enabled": deletion_enabled(),
        "auto_reminders_enabled": auto_reminders_enabled(),
        "next_cleanup_at": next_cleanup_at(now).isoformat(),
        "rules": {"trial_grace_days": TRIAL_GRACE_DAYS, "lapsed_grace_days": LAPSED_GRACE_DAYS,
                  "monthly_history_days": MONTHLY_HISTORY_DAYS, "annual_history_days": ANNUAL_HISTORY_DAYS},
    }


# ------------------------------------------------------------------ correos
def reminder_message(group: str, delete_at: datetime | None) -> tuple[str, str]:
    when = ""
    if delete_at:
        local = delete_at.astimezone(MEXICO_CITY)
        when = f" el {local.day:02d}/{local.month:02d}/{local.year}"
    if group == "trial":
        subject = "Tu prueba de Donexto terminó: suscríbete para conservar tu cuenta"
        lead = "Tu prueba gratis de Donexto terminó."
    else:
        subject = "Tu suscripción de Donexto venció: renuévala para conservar tu cuenta"
        lead = "Tu suscripción de Donexto no se renovó."
    body = (
        f"Hola:\n\n{lead} Si no te suscribes, tu cuenta y sus datos se borrarán{when}.\n\n"
        "Plan mensual: US$19.99 / €19.99. Plan anual: US$175.99 / €175.99.\n"
        "Suscríbete en https://app.donexto.com\n\n"
        "Si ya no quieres usar Donexto, no tienes que hacer nada.\n\n— Donexto"
    )
    return subject, body


def _default_sender(to_addr: str, subject: str, body: str) -> bool:
    from app.services.support_notify import _send_via_resend

    return _send_via_resend(to_addr, subject, body)


def send_subscribe_reminders(
    client: Any,
    group: str,
    *,
    now: datetime | None = None,
    sender: Callable[[str, str, str], bool] | None = None,
) -> dict[str, int]:
    """Botón de /admin: manda el recordatorio a todo un grupo (trial|lapsed)."""
    if group not in {"trial", "lapsed"}:
        raise ValueError("Grupo inválido.")
    now = now or datetime.now(timezone.utc)
    send = sender or _default_sender
    overview = lifecycle_overview(client, now)
    rows = overview["trials"] if group == "trial" else overview["lapsed"]
    result = {"sent": 0, "skipped_protected": 0, "skipped_no_email": 0, "skipped_active": 0, "failed": 0}
    for row in rows:
        # Solo cuentas cuya prueba o suscripción ya terminó (no pruebas en curso).
        if row.get("phase") != "por_borrar":
            result["skipped_active"] += 1
            continue
        if row.get("protected") or not row.get("email"):
            if not row.get("email"):
                result["skipped_no_email"] += 1
            else:
                result["skipped_protected"] += 1
            continue
        subject, body = reminder_message(group, _parse(row.get("delete_at")))
        try:
            ok = send(row["email"], subject, body)
        except Exception:
            logger.warning("subscribe reminder failed", exc_info=True)
            ok = False
        if ok:
            result["sent"] += 1
            try:
                client.table("account_plans").update(
                    {"last_manual_reminder_at": now.isoformat()}
                ).eq("user_id", row["user_id"]).execute()
            except Exception:
                logger.info("reminder stamp failed", exc_info=True)
        else:
            result["failed"] += 1
    logger.info("subscribe reminders group=%s result=%s", group, result)
    return result


# ------------------------------------------------------------------ limpieza
def _delete_user(client: Any, user_id: str) -> None:
    from app.api.admin_ops import cleanup_user_records

    cleanup_user_records(client, user_id)
    client.auth.admin.delete_user(user_id)


def run_daily_cleanup(
    client: Any,
    *,
    now: datetime | None = None,
    delete: bool | None = None,
    send_reminders: bool | None = None,
    sender: Callable[[str, str, str], bool] | None = None,
    deleter: Callable[[Any, str], None] | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    delete = deletion_enabled() if delete is None else delete
    send_reminders = auto_reminders_enabled() if send_reminders is None else send_reminders
    send = sender or _default_sender
    remove = deleter or _delete_user
    try:
        plans = _rows(client.table("account_plans").select("*").execute())
    except Exception:
        logger.warning("account cleanup: account_plans unavailable", exc_info=True)
        plans = []
    emails = _emails_by_id(client, [str(p["user_id"]) for p in plans if p.get("user_id")])
    protected = protected_emails()
    counts = {"trial_due": 0, "lapsed_due": 0, "deleted": 0, "skipped_protected": 0,
              "reminders_mid": 0, "reminders_final": 0, "would_delete": 0, "errors": 0}
    for plan in plans:
        user_id = str(plan.get("user_id") or "")
        retention = retention_for(plan, now)
        if not user_id or retention is None:
            continue
        email = emails.get(user_id, "")
        # Falla cerrada: sin correo conocido no se puede comprobar la protección.
        if not email or email in protected:
            counts["skipped_protected"] += 1
            continue
        if now >= retention.delete_at:
            counts["trial_due" if retention.group == "trial" else "lapsed_due"] += 1
            if delete:
                try:
                    remove(client, user_id)
                    counts["deleted"] += 1
                except Exception:
                    counts["errors"] += 1
                    logger.warning("account cleanup delete failed", exc_info=True)
            else:
                counts["would_delete"] += 1
            continue
        if not send_reminders or not email:
            continue
        for key, due_at, column in (
            ("reminders_final", retention.final_reminder_at, "reminder_final_sent_at"),
            ("reminders_mid", retention.midpoint_at, "reminder_mid_sent_at"),
        ):
            if now >= due_at and not plan.get(column):
                subject, body = reminder_message(retention.group, retention.delete_at)
                try:
                    if send(email, subject, body):
                        counts[key] += 1
                        stamp = {column: now.isoformat()}
                        if column == "reminder_final_sent_at":
                            stamp["reminder_mid_sent_at"] = plan.get("reminder_mid_sent_at") or now.isoformat()
                        client.table("account_plans").update(stamp).eq("user_id", user_id).execute()
                except Exception:
                    counts["errors"] += 1
                    logger.warning("account cleanup reminder failed", exc_info=True)
                break
    dry_run = not delete
    logger.info("account cleanup dry_run=%s counts=%s", dry_run, counts)
    try:
        client.table("account_cleanup_runs").insert({
            "dry_run": dry_run,
            "trial_due": counts["trial_due"],
            "lapsed_due": counts["lapsed_due"],
            "deleted": counts["deleted"],
            "skipped_protected": counts["skipped_protected"],
            "reminders_mid": counts["reminders_mid"],
            "reminders_final": counts["reminders_final"],
            "details": counts,
        }).execute()
    except Exception:
        logger.info("account cleanup run log failed", exc_info=True)
    return {"dry_run": dry_run, "ran_at": now.isoformat(), **counts}


def _worker() -> None:
    from app.database.supabase import get_supabase_client

    while _flag("ACCOUNT_CLEANUP_SCHEDULER_ENABLED", "true"):
        now = datetime.now(timezone.utc)
        wait = max(30.0, (next_cleanup_at(now) - now).total_seconds())
        time.sleep(wait)
        try:
            run_daily_cleanup(get_supabase_client())
        except Exception:
            logger.warning("account cleanup cycle failed", exc_info=True)


def start_account_cleanup_scheduler() -> bool:
    global _started
    if not _flag("ACCOUNT_CLEANUP_SCHEDULER_ENABLED", "true"):
        return False
    with _lock:
        if _started:
            return False
        _started = True
    threading.Thread(target=_worker, name="donexto-account-cleanup", daemon=True).start()
    return True
