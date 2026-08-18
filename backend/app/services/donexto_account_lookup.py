"""Helpers puros para saber si un correo ya tiene cuenta Donexto."""

from __future__ import annotations

from typing import Any


def normalize_lookup_email(value: str) -> str | None:
    clean = value.strip().lower()
    at = clean.find("@")
    if at < 1 or "." not in clean[at + 1 :] or len(clean) > 320:
        return None
    return clean


def admin_users_exist(payload: Any, email: str) -> bool:
    if not isinstance(payload, dict):
        return False
    users = payload.get("users")
    if not isinstance(users, list):
        user = payload.get("user")
        if isinstance(user, dict):
            found = str(user.get("email") or "").strip().lower()
            return found == email
        return False
    for row in users:
        if not isinstance(row, dict):
            continue
        found = str(row.get("email") or "").strip().lower()
        if found == email:
            return True
    return False
