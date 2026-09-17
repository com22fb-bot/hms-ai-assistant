#!/usr/bin/env python3
"""Clean legacy OAuth Donexto verification flags.

Dry-run is the default. Use --apply only after reviewing the listed users.
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
from app.services.oauth_verification_cleanup import (  # noqa: E402
    clear_legacy_oauth_verification,
    is_legacy_oauth_verified_user,
)

PAGE_SIZE = 100


def _users_from_response(response: Any) -> list[Any]:
    users = getattr(response, "users", None)
    if users is None and isinstance(response, dict):
        users = response.get("users")
    return users if isinstance(users, list) else []


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
        description="Limpia flags donexto_verified heredados de OAuth."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplica la limpieza; sin esta opción solo muestra candidatos.",
    )
    args = parser.parse_args()

    client = get_supabase_client()
    candidates = [user for user in iter_users(client) if is_legacy_oauth_verified_user(user)]
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"{mode}: {len(candidates)} usuario(s) OAuth candidato(s).")
    for user in candidates:
        user_id = str(getattr(user, "id", "") or "")
        email = str(getattr(user, "email", "") or "")
        print(f"- {user_id} {email}".rstrip())

    if args.apply:
        for user in candidates:
            clear_legacy_oauth_verification(client, user)
        print(f"Limpiados: {len(candidates)} usuario(s).")
    else:
        print("No se modificó ninguna cuenta. Revisa la lista y vuelve a ejecutar con --apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
