#!/usr/bin/env bash
# Prueba aislada: Postgres temporal local. Uso: bash supabase/tests/run_admin_purge_user_test.sh
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
bin="$(ls -d /usr/lib/postgresql/*/bin 2>/dev/null | tail -1)"; PATH="$bin:$PATH"
dir="$(mktemp -d)"; trap 'pg_ctl -D "$dir" -m immediate stop >/dev/null 2>&1 || true; rm -rf "$dir"' EXIT
initdb -D "$dir" -U postgres >/dev/null
pg_ctl -D "$dir" -o "-k $dir -c listen_addresses=''" -l "$dir/log" start >/dev/null
psql() { command psql -h "$dir" -U postgres -d postgres -v ON_ERROR_STOP=1 -q "$@"; }
psql -f "$here/admin_purge_user_fixture.sql"
psql -f "$here/../migrations/20261022_001_admin_purge_user_test_accounts.sql"
psql -f "$here/admin_purge_user_test.sql"
