"""Lista de aviso: correo + proveedor cuando el buzón aún no se puede leer."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

ALLOWED_PROVIDERS = frozenset(
    {"gmail", "yahoo", "apple", "hotmail", "other", "google_workspace"}
)


def normalize_waitlist_provider(provider: str) -> str:
    raw = (provider or "").strip().lower()
    if raw in {"google", "google_workspace"}:
        return "gmail"
    if raw in {"icloud", "apple"}:
        return "apple"
    if raw in {"microsoft", "outlook", "hotmail", "live", "msn"}:
        return "hotmail"
    if raw in ALLOWED_PROVIDERS:
        return raw
    return "other"


def persist_waitlist(email: str, provider: str) -> dict[str, Any]:
    clean_email = (email or "").strip().lower()
    clean_provider = normalize_waitlist_provider(provider)
    try:
        from app.database.supabase import get_supabase_client

        client = get_supabase_client()
        existing = (
            client.table("mailbox_waitlist")
            .select("id,email,provider,created_at")
            .eq("email", clean_email)
            .eq("provider", clean_provider)
            .limit(1)
            .execute()
        )
        rows = getattr(existing, "data", None) or []
        if isinstance(rows, list) and rows:
            row = rows[0]
            return {
                "status": "ok",
                "already": True,
                "email": clean_email,
                "provider": clean_provider,
                "created_at": row.get("created_at"),
            }

        inserted = (
            client.table("mailbox_waitlist")
            .insert(
                {
                    "email": clean_email,
                    "provider": clean_provider,
                }
            )
            .execute()
        )
        created = (getattr(inserted, "data", None) or [None])[0] or {}
        return {
            "status": "ok",
            "already": False,
            "email": clean_email,
            "provider": clean_provider,
            "created_at": created.get("created_at"),
        }
    except Exception as error:  # noqa: BLE001 — la tabla puede no existir aún
        logger.info("No se persistió mailbox_waitlist: %s", error)
        return {
            "status": "ok",
            "already": False,
            "email": clean_email,
            "provider": clean_provider,
            "created_at": None,
            "stored": False,
            "message": "Te apuntamos. El aviso queda pendiente de guardar.",
        }
