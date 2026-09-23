#!/usr/bin/env python3
"""Backfill trusted Donexto app_metadata for historical verified accounts.

The verification email is only for a new signup. After Verificar succeeds,
``mark_donexto_verified`` stores ``app_metadata.donexto_verified`` and
``donexto_verification_source=email``. Some early accounts (including the
first Google OAuth account) only have ``user_metadata.donexto_verified=true``.
The live auth check does not trust that client-writable field, so those
sessions asked for the mail again on every login.

Run this once, from the Codespace or a cloud shell that already has
``SUPABASE_URL`` and ``SUPABASE_SECRET_KEY`` (service role). Do not run it
from the Windows laptop, and do not schedule it.

When to run:
1. After this change is deployed.
2. Dry-run first (the default). Read every email. ``user_metadata`` can be
   edited by the client, so only accounts that really finished Verificar
   before the app_metadata migration should be applied.
3. Re-run with ``--apply`` for that reviewed list. ``--email`` limits the
   write to specific mailboxes.
4. Safe to run again later: accounts that already have the trusted email
   source are skipped, and the OAuth cleanup script will not remove it.

Dry-run is the default. ``--apply`` writes app_metadata.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database.supabase import get_supabase_client  # noqa: E402
from app.services.donexto_verified_backfill import (  # noqa: E402
    apply_donexto_verified_backfill,
    is_donexto_verified_backfill_candidate,
)

PAGE_SIZE = 100


def _users_from_response(response: Any) -> list[Any]:
    users = getattr(response, "users", None)
    if users is None and isinstance(response, dict):
        users = response.get("users")
    return users if isinstance(users, list) else []


def _email(user: Any) -> str:
    raw = user.get("email") if isinstance(user, dict) else getattr(user, "email", "")
    return str(raw or "").strip().lower()


def _user_id(user: Any) -> str:
    raw = user.get("id") if isinstance(user, dict) else getattr(user, "id", "")
    return str(raw or "").strip()


def iter_users(client: Any):
    page = 1
    while True:
        response = client.auth.admin.list_users(
            page=page,
            per_page=PAGE_SIZE,
        )
        users = _users_from_response(response)
        yield from users
        if len(users) < PAGE_SIZE:
            return
        page += 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Migra user_metadata.donexto_verified histórico a app_metadata "
            "con donexto_verification_source=email. Dry-run por defecto."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Escribe app_metadata. Sin esta opción solo lista candidatos.",
    )
    parser.add_argument(
        "--email",
        action="append",
        default=[],
        help="Limita el lote a este correo. Puede repetirse.",
    )
    args = parser.parse_args()
    only = {item.strip().lower() for item in args.email if item and item.strip()}

    client = get_supabase_client()
    candidates = []
    for user in iter_users(client):
        if not is_donexto_verified_backfill_candidate(user):
            continue
        if only and _email(user) not in only:
            continue
        candidates.append(user)

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"{mode}: {len(candidates)} cuenta(s) con verificación histórica sin app_metadata confiable.")
    for user in candidates:
        print(f"- {_user_id(user)} {_email(user)}".rstrip())

    if args.apply:
        applied = 0
        for user in candidates:
            if apply_donexto_verified_backfill(client, user):
                applied += 1
        print(f"Migradas: {applied} cuenta(s).")
    else:
        print(
            "No se modificó ninguna cuenta. Revisa la lista y vuelve a "
            "ejecutar con --apply solo si cada correo ya pulsó Verificar."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
