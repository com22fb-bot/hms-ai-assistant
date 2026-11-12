#!/usr/bin/env bash
# Integración PR #181 (borrado v2) × PR #184 (normalización) en Postgres efímero.
# Orden previsto: esquema prod → #181 (20261023_002) → #184 001 → 003 → 002 → borrado dry-run y real.
# Orden inválido: 002 sin #181 (o con la función v1 incompatible) → debe abortar con mensaje claro.
# Los archivos de la otra PR se leen de git (REF181 / REF184) si no están en el árbol de trabajo.
set -euo pipefail
cd "$(dirname "$0")/../../.."
REF181=${REF181:-origin/admin/purge-cascada}
REF184=${REF184:-origin/db/normalizacion-propuesta}
ADMIN="psql -X -v ON_ERROR_STOP=1 -q -tA ${PGURL:-} -d postgres"
TMP=$(mktemp -d)
get(){ if [ -f "$2" ]; then cp "$2" "$TMP/$3"; else git show "$1:$2" > "$TMP/$3"; fi; }
get "$REF184" supabase/tests/normalizacion/schema_prod.sql schema.sql
get "$REF181" supabase/migrations/20261023_002_admin_purge_user_v2.sql m181.sql
get main      supabase/migrations/20261022_001_admin_purge_user_test_accounts.sql m181_v1.sql 2>/dev/null || git show origin/main:supabase/migrations/20261022_001_admin_purge_user_test_accounts.sql > "$TMP/m181_v1.sql"
for n in 001_drop_legado_sin_codigo 003_estructura_dominios_y_claves 002_drop_legado_listas_limpieza; do
  get "$REF184" supabase/prepared/normalizacion/$n.up.sql $n.sql; done
S=supabase/tests/integracion_181_184
pass=0; ok(){ echo "PASS $1"; pass=$((pass+1)); }; fail(){ echo "FAIL $1"; exit 1; }
newdb(){ $ADMIN -c "drop database if exists $1" -c "create database $1" >/dev/null
  P="psql -X -v ON_ERROR_STOP=1 -q -tA ${PGURL:-} -d $1"
  $P -c "do \$\$ begin if not exists (select 1 from pg_roles where rolname='anon') then create role anon; end if;
    if not exists (select 1 from pg_roles where rolname='authenticated') then create role authenticated; end if;
    if not exists (select 1 from pg_roles where rolname='service_role') then create role service_role; end if; end \$\$" >/dev/null
  $P -f "$TMP/schema.sql" >/dev/null; }
U=00000000-0000-0000-0000-0000000000aa

# --- Orden inválido 1: 002 sin la migración #181 ---
newdb ix1; $P -f $TMP/001_drop_legado_sin_codigo.sql; $P -f $TMP/003_estructura_dominios_y_claves.sql
if out=$($P -f $TMP/002_drop_legado_listas_limpieza.sql 2>&1); then fail "002 sin #181 debía abortar"; fi
echo "$out" | grep -q "requiere la migración 20261023_002" && ok "002 sin #181 aborta: $(echo "$out" | grep -o 'ERROR: .*' | head -1)"
[ "$($P -c "select to_regclass('public.users') is not null")" = t ] && ok "002 abortada no borró public.users"

# --- Orden inválido 2: con la función v1 (referencia public.users) ---
newdb ix2; $P -f $TMP/m181_v1.sql >/dev/null; $P -f $TMP/001_drop_legado_sin_codigo.sql; $P -f $TMP/003_estructura_dominios_y_claves.sql
if out=$($P -f $TMP/002_drop_legado_listas_limpieza.sql 2>&1); then fail "002 con v1 debía abortar"; fi
echo "$out" | grep -q "requiere la migración 20261023_002" && ok "002 con borrado v1 incompatible aborta: $(echo "$out" | grep -o 'ERROR: .*' | head -1)"

# --- Orden inválido 3: #181 aplicada pero admin_purge_targets vuelve a listar una tabla legada ---
newdb ix3; $P -f $TMP/m181.sql >/dev/null 2>&1; $P -f $TMP/001_drop_legado_sin_codigo.sql; $P -f $TMP/003_estructura_dominios_y_claves.sql
$P -c "insert into public.admin_purge_targets values ('tasks','user_id','profile',5,false,'regresión')"
if out=$($P -f $TMP/002_drop_legado_listas_limpieza.sql 2>&1); then fail "002 con lista legada debía abortar"; fi
echo "$out" | grep -q "admin_purge_targets aún referencia tasks" && ok "002 aborta si admin_purge_targets referencia tablas legadas"

# --- Orden previsto ---
newdb iok; $P -f $TMP/m181.sql >/dev/null 2>&1 && ok "#181 (20261023_002) aplicada sobre esquema prod"
$P -f $TMP/001_drop_legado_sin_codigo.sql && ok "#184 001 aplicada"
$P -f $TMP/003_estructura_dominios_y_claves.sql && ok "#184 003 aplicada"
$P -f $TMP/002_drop_legado_listas_limpieza.sql && ok "#184 002 aplicada (guardia #181 satisfecha)"
[ "$($P -c "select count(*) from pg_tables where schemaname='public' and tablename in ('users','tasks','notifications','reminders','audit_log','mail_accounts','alerts','emails','user_workspaces')")" = 0 ] && ok "tablas legadas eliminadas"
$P -f $S/seed.sql
snap(){ $P -c "select json_build_object('acc',(select json_agg(row_to_json(a) order by id) from (select id,status,connected_by_profile_id from communication_accounts) a),
  'msgs',(select count(*) from communication_messages),'att',(select count(*) from attachments),'cred',(select count(*) from oauth_credentials),
  'auth',(select count(*) from auth.users),'ws',(select count(*) from workspaces),'q',(select count(*) from admin_storage_purge_queue),'ev',(select count(*) from admin_events))"; }
B=$(snap)
PLAN=$($P -c "select admin_purge_user('$U', true)")
echo "DRY-RUN: $PLAN"
[ "$(snap)" = "$B" ] && ok "dry-run sin cambios"
echo "$PLAN" | grep -q '"users": "omitida_inexistente"' && ok "legado users = omitida_inexistente"
REAL=$($P -c "select admin_purge_user('$U', false) - 'purge_ref' - 'storage_paths'")
echo "REAL: $REAL"
[ "$($P -c "select (('$REAL')::jsonb->'counts') = (('$PLAN')::jsonb->'counts')")" = t ] && ok "real = plan"
[ "$($P -c "select count(*) from auth.users where id='$U'")" = 0 ] && ok "usuario borrado"
[ "$($P -c "select status||','||connected_by_profile_id||','||(select count(*) from communication_messages m where m.account_id=a.id) from communication_accounts a where id='20000000-0000-0000-0000-000000000002'")" = "disconnected,00000000-0000-0000-0000-0000000000bb,4" ] && ok "buzón compartido conservado y reasignado (4 correos)"
ORPH=$($P -c "select (select count(*) from communication_messages m left join communication_accounts a on a.id=m.account_id where a.id is null)
 + (select count(*) from communication_threads t left join communication_accounts a on a.id=t.account_id where a.id is null)
 + (select count(*) from attachments x left join communication_messages m on m.id=x.message_id where m.id is null)
 + (select count(*) from oauth_credentials o left join communication_accounts a on a.id=o.account_id where a.id is null)
 + (select count(*) from communication_accounts a left join workspaces w on w.id=a.workspace_id where w.id is null)
 + (select count(*) from workspace_members m left join profiles p on p.id=m.profile_id where p.id is null)
 + (select count(*) from communication_accounts where connected_by_profile_id='$U')")
[ "$ORPH" = 0 ] && ok "sin huérfanos"
[ "$($P -c "select count(*) from admin_storage_purge_queue where status='pendiente'")" = 4 ] && ok "4 rutas en cola Storage"
echo "TOTAL PASS=$pass"
[ "$pass" -eq 16 ] || fail "se esperaban 16 aserciones ($pass)"
