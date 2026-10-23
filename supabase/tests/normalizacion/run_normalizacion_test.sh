#!/usr/bin/env bash
# Prueba en Postgres efímero: esquema de producción (solo estructura) → up 001..003 → aserciones → down 003..001 → catálogo idéntico.
set -euo pipefail
cd "$(dirname "$0")/../../.."
PSQL="psql -X -v ON_ERROR_STOP=1 -q -tA ${PGURL:-}"
M=supabase/prepared/normalizacion
T=supabase/tests/normalizacion
pass=0; ok(){ echo "PASS $1"; pass=$((pass+1)); }
fail(){ echo "FAIL $1"; exit 1; }
snap(){ $PSQL -c "select string_agg(x, E'\n' order by x) from (
  select 'T '||c.relname||' '||string_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod)||':'||a.attnotnull, ',' order by a.attnum) x
    from pg_class c join pg_attribute a on a.attrelid=c.oid and a.attnum>0 and not a.attisdropped
   where c.relnamespace='public'::regnamespace and c.relkind='r' group by c.relname
  union all select 'C '||conrelid::regclass||' '||conname||' '||pg_get_constraintdef(oid) from pg_constraint where connamespace='public'::regnamespace
  union all select 'F '||p.oid::regprocedure::text from pg_proc p where p.pronamespace='public'::regnamespace) s"; }
expect_err(){ if $PSQL -c "$2" >/dev/null 2>&1; then fail "$1"; else ok "$1"; fi; }

$PSQL -c "set client_min_messages=warning; drop schema if exists public cascade; drop schema if exists auth cascade; create schema public;"
$PSQL -f $T/schema_prod.sql
[ "$($PSQL -c "select count(*) from pg_tables where schemaname='public'")" = 49 ] && ok "esquema prod cargado (49 tablas)"
BEFORE=$(snap)

# Guardia: si una tabla a borrar tiene filas, 001 aborta sin tocar nada
$PSQL -c "insert into public.ops_r3_operation (script) values ('prueba')"
expect_err "001 aborta si hay filas" "\\i $M/001_drop_legado_sin_codigo.up.sql"
[ "$($PSQL -c "select to_regclass('public.alerts') is not null and to_regclass('public.ops_r3_operation') is not null")" = t ] && ok "001 abortado no borró nada"
$PSQL -c "delete from public.ops_r3_operation"

expect_err "002 exige 001 previa" "\\i $M/002_drop_legado_listas_limpieza.up.sql"
$PSQL -f $M/001_drop_legado_sin_codigo.up.sql
$PSQL -f $M/002_drop_legado_listas_limpieza.up.sql
[ "$($PSQL -c "select count(*) from pg_tables where schemaname='public'")" = 36 ] && ok "A: 13 tablas legadas fuera (36 quedan)"
[ "$($PSQL -c "select count(*) from pg_tables where schemaname='public' and tablename in ('communication_accounts','communication_messages','profiles','workspaces','intelligent_cases','attachments','communication_tasks','ai_analysis')")" = 8 ] && ok "tablas en uso intactas"

$PSQL -f $M/003_estructura_dominios_y_claves.up.sql
# datos de prueba
$PSQL <<'S'
insert into auth.users(id) values ('00000000-0000-0000-0000-0000000000a1');
insert into public.profiles(id,updated_at) values ('00000000-0000-0000-0000-0000000000a1',now());
insert into public.workspaces(id,name) values ('00000000-0000-0000-0000-00000000000a','w1'),('00000000-0000-0000-0000-00000000000b','w2');
insert into public.communication_accounts(id,workspace_id,provider,status,email,address_key) values
 ('00000000-0000-0000-0000-0000000000c1','00000000-0000-0000-0000-00000000000a','google','active','a@x.com','a@x.com'),
 ('00000000-0000-0000-0000-0000000000c2','00000000-0000-0000-0000-00000000000b','yahoo','active','b@x.com','b@x.com');
insert into public.communication_threads(id,account_id,external_thread_id) values ('00000000-0000-0000-0000-0000000000d1','00000000-0000-0000-0000-0000000000c1','t1');
S
expect_err "B: status de buzón inválido rechazado" "update public.communication_accounts set status='borrado_raro' where id='00000000-0000-0000-0000-0000000000c1'"
expect_err "B: proveedor inválido rechazado" "update public.communication_accounts set provider='hotmial' where id='00000000-0000-0000-0000-0000000000c1'"
expect_err "B: cc no-arreglo rechazado" "insert into public.communication_messages(account_id,thread_id,external_message_id,cc) values ('00000000-0000-0000-0000-0000000000c1','00000000-0000-0000-0000-0000000000d1','m0','{\"a\":1}')"
$PSQL -c "insert into public.communication_messages(account_id,thread_id,external_message_id,cc) values ('00000000-0000-0000-0000-0000000000c1','00000000-0000-0000-0000-0000000000d1','m1','[\"z@x.com\"]')" && ok "B: mensaje válido aceptado"
expect_err "B: mensaje con hilo de OTRO buzón rechazado" "insert into public.communication_messages(account_id,thread_id,external_message_id) values ('00000000-0000-0000-0000-0000000000c2','00000000-0000-0000-0000-0000000000d1','m2')"
expect_err "B: caso con buzón de OTRO espacio rechazado" "insert into public.intelligent_cases(workspace_id,account_id,title) values ('00000000-0000-0000-0000-00000000000b','00000000-0000-0000-0000-0000000000c1','x')"
$PSQL -c "delete from public.communication_accounts where id='00000000-0000-0000-0000-0000000000c1'"
[ "$($PSQL -c "select count(*) from public.communication_messages")" = 0 ] && ok "B: cascada sin huérfanos al borrar buzón"
$PSQL -c "delete from public.communication_accounts; delete from public.workspaces; delete from public.profiles; delete from auth.users"

$PSQL -f $M/003_estructura_dominios_y_claves.down.sql
$PSQL -f $M/002_drop_legado_listas_limpieza.down.sql
$PSQL -f $M/001_drop_legado_sin_codigo.down.sql
AFTER=$(snap)
if [ "$BEFORE" = "$AFTER" ]; then ok "reversible: catálogo después de down = original"; else diff <(echo "$BEFORE") <(echo "$AFTER") | head -20; fail "reversible"; fi
echo "TOTAL PASS=$pass"
