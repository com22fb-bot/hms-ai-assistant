"""Preferencias del tablero Núcleo IA.

Si la migración todavía no está aplicada, el mismo JSON vive en
profiles.metadata.nucleo para que la app no pierda el tema ni las reglas.
"""

from __future__ import annotations

from typing import Any

from app.security.identity import require_request_context
from app.services.nucleo_prefs import sanitize_preferences, schema_gap
from app.services.oauth_storage import OAuthStorage


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


def _metadata_nucleo(client: Any, profile_id: str) -> dict[str, Any]:
    profile = _first(
        client.table("profiles")
        .select("metadata")
        .eq("id", profile_id)
        .limit(1)
        .execute()
    )
    metadata = (profile or {}).get("metadata")
    if not isinstance(metadata, dict):
        return {}
    nucleo = metadata.get("nucleo")
    return nucleo if isinstance(nucleo, dict) else {}


def _write_metadata(client: Any, profile_id: str, preferences: dict[str, Any]) -> None:
    profile = _first(
        client.table("profiles")
        .select("metadata")
        .eq("id", profile_id)
        .limit(1)
        .execute()
    )
    metadata = (profile or {}).get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    metadata = {**metadata, "nucleo": preferences}
    client.table("profiles").update({"metadata": metadata}).eq("id", profile_id).execute()


def _mirror_rules(
    client: Any,
    *,
    profile_id: str,
    workspace_id: str,
    rules: list[dict[str, Any]],
) -> None:
    try:
        client.table("donexto_alert_rules").delete().eq("profile_id", profile_id).execute()
        if not rules:
            return
        client.table("donexto_alert_rules").insert(
            [
                {
                    "profile_id": profile_id,
                    "workspace_id": workspace_id,
                    "rule_id": rule["id"],
                    "kind": rule["kind"],
                    "value": rule["value"],
                    "enabled": rule["enabled"],
                    "area": rule.get("area"),
                    "updated_at": "now()",
                }
                for rule in rules
            ]
        ).execute()
    except Exception as error:
        if not schema_gap(error):
            raise


def load_preferences() -> dict[str, Any]:
    context = require_request_context()
    client = OAuthStorage().client
    try:
        row = _first(
            client.table("donexto_preferences")
            .select("preferences")
            .eq("profile_id", context.user.id)
            .limit(1)
            .execute()
        )
        stored = (row or {}).get("preferences")
        if isinstance(stored, dict) and stored:
            return stored
    except Exception as error:
        if not schema_gap(error):
            raise
    return _metadata_nucleo(client, context.user.id)


def store_preferences(raw: Any) -> dict[str, Any]:
    context = require_request_context()
    clean = sanitize_preferences(raw)
    client = OAuthStorage().client
    saved_table = False
    try:
        existing = _first(
            client.table("donexto_preferences")
            .select("profile_id")
            .eq("profile_id", context.user.id)
            .limit(1)
            .execute()
        )
        payload = {
            "workspace_id": context.workspace_id,
            "preferences": clean,
            "updated_at": "now()",
        }
        if existing:
            client.table("donexto_preferences").update(payload).eq(
                "profile_id", context.user.id
            ).execute()
        else:
            client.table("donexto_preferences").insert(
                {"profile_id": context.user.id, **payload}
            ).execute()
        saved_table = True
    except Exception as error:
        if not schema_gap(error):
            raise
    _write_metadata(client, context.user.id, clean)
    if saved_table:
        _mirror_rules(
            client,
            profile_id=context.user.id,
            workspace_id=context.workspace_id,
            rules=list(clean["alertRules"]),
        )
    return clean
