#!/usr/bin/env bash
# Pruebas de supabase/prepared/revoke-urgente sobre una BD con estructura de prod (+ grants_prod.sql).
# Uso: PGURL="-h … -p … -U postgres -d …" bash supabase/tests/revoke-urgente/run.sh   (solo imprime PASS/FAIL y conteos)
set -euo pipefail
cd "$(dirname "$0")/../../.."
PSQL="psql -X -v ON_ERROR_STOP=1 -q -tA ${PGURL:-}"
M=supabase/prepared/revoke-urgente
pass=0; ok(){ echo "PASS $1"; pass=$((pass+1)); }; fail(){ echo "FAIL $1"; exit 1; }
chk(){ v=$($PSQL -c "$2"); [ "$v" = "$3" ] && ok "$1" || fail "$1 (esperado $3, obtuvo ${v:-vacío})"; }
err(){ if $PSQL -c "$2" >/dev/null 2>&1; then fail "$1"; else ok "$1"; fi; }
snap(){ $PSQL -c "select md5(string_agg(x, E'\n' order by x)) from (
  select 'C '||conrelid::regclass||' '||conname||' '||pg_get_constraintdef(oid) x from pg_constraint where connamespace='public'::regnamespace
  union all select 'I '||indexdef from pg_indexes where schemaname='public'
  union all select 'P '||policyname||' '||tablename||coalesce(qual,'')||coalesce(with_check,'') from pg_policies where schemaname='public'
  union all select 'G '||table_name||' '||grantee||' '||privilege_type from information_schema.role_table_grants where table_schema='public' and grantee in ('anon','authenticated','service_role')) s"; }
A=00000000-0000-0000-0000-0000000000a1; B=00000000-0000-0000-0000-0000000000b1
WA=00000000-0000-0000-0000-00000000aa01; WB=00000000-0000-0000-0000-00000000bb01
CA=00000000-0000-0000-0000-0000000ca001; CB=00000000-0000-0000-0000-0000000cb001
TA=00000000-0000-0000-0000-0000000da001; TB=00000000-0000-0000-0000-0000000db001
as(){ echo "set request.jwt.claim.sub = '$2'; set request.jwt.claims = '{\"sub\":\"$2\",\"role\":\"$1\"}'; set role $1;"; }
cleanup(){ $PSQL -c "reset role; delete from public.admin_allowlist where user_id in ('$A','$B'); delete from public.communication_accounts where id in ('$CA','$CB'); delete from public.workspace_members where profile_id in ('$A','$B'); delete from public.workspaces where id in ('$WA','$WB'); delete from public.profiles where id in ('$A','$B'); delete from auth.users where id in ('$A','$B');" >/dev/null; }
trap cleanup EXIT

BEFORE=$(snap)
MSG0=$($PSQL -c "select count(*) from public.communication_messages")
$PSQL -f $M/001_revoke_anon_authenticated.up.sql && ok "up aplicada"
$PSQL -f $M/001_revoke_anon_authenticated.up.sql && ok "up idempotente (2ª pasada)"
chk "datos sin cambios" "select count(*) from public.communication_messages" "$MSG0"

# datos sintéticos: 2 usuarios en espacios individuales, 1 buzón y 1 hilo cada uno
$PSQL <<S
insert into auth.users(id,email) values ('$A','a@prueba.invalid'),('$B','b@prueba.invalid');
insert into public.profiles(id) values ('$A'),('$B') on conflict (id) do nothing;
insert into public.workspaces(id,name) values ('$WA','wa'),('$WB','wb');
insert into public.workspace_members(workspace_id,profile_id) values ('$WA','$A'),('$WB','$B');
insert into public.communication_accounts(id,workspace_id,provider,status,email) values ('$CA','$WA','google','active','a@prueba.invalid'),('$CB','$WB','yahoo','active','b@prueba.invalid');
insert into public.communication_threads(id,account_id,external_thread_id) values ('$TA','$CA','ta'),('$TB','$CB','tb');
S
$PSQL -c "set role service_role; insert into public.communication_messages(account_id,thread_id,external_message_id) values ('$CA','$TA','m1')" && ok "service_role inserta mensaje (ruta del sync)"
err "mensaje duplicado (buzón, id externo) rechazado" "insert into public.communication_messages(account_id,thread_id,external_message_id) values ('$CA','$TA','m1')"
err "hilo duplicado (buzón, id externo) rechazado" "insert into public.communication_threads(account_id,external_thread_id) values ('$CA','ta')"
$PSQL -c "insert into public.intelligent_cases(id,workspace_id,account_id,title) values ('00000000-0000-0000-0000-0000000ee001','$WA','$CA','caso')"
$PSQL -c "insert into public.case_messages(case_id,message_id) select '00000000-0000-0000-0000-0000000ee001', id from public.communication_messages where external_message_id='m1' and account_id='$CA'"
err "mensaje en dos casos rechazado (case_messages único por mensaje)" "insert into public.intelligent_cases(id,workspace_id,account_id,title) values ('00000000-0000-0000-0000-0000000ee002','$WA','$CA','c2'); insert into public.case_messages(case_id,message_id) select '00000000-0000-0000-0000-0000000ee002', id from public.communication_messages where external_message_id='m1' and account_id='$CA'"
$PSQL -c "insert into public.gmail_sync_jobs(workspace_id,account_id,status) values ('$WA','$CA','queued')"
err "2º trabajo de sync activo del mismo buzón rechazado" "insert into public.gmail_sync_jobs(workspace_id,account_id,status) values ('$WA','$CA','running')"

# permisos efectivos (demostrados, no supuestos)
chk "service_role ve el mensaje sintético" "set role service_role; select count(*) from public.communication_messages where account_id='$CA'" 1
$PSQL -c "set role service_role; update public.gmail_sync_jobs set status='running' where account_id='$CA'" && ok "service_role actualiza trabajo de sync"
for t in communication_messages communication_threads communication_tasks attachments ai_analysis gmail_sync_jobs system_incidents case_reclassification_runs; do
  err "anon: SELECT en $t denegado" "set role anon; select 1 from public.$t limit 1"
  err "authenticated: SELECT en $t denegado" "$(as authenticated $A) select 1 from public.$t limit 1"
done
err "anon: TRUNCATE en gmail_sync_jobs denegado" "set role anon; truncate public.gmail_sync_jobs"
chk "authenticated A ve solo su perfil (aislamiento; ruta del frontend)" "$(as authenticated $A) select string_agg(id::text,',') from public.profiles where id in ('$A','$B')" "$A"
chk "authenticated A ve solo el buzón de su espacio (política hms_accounts_select_member)" "$(as authenticated $A) select string_agg(id::text,',') from public.communication_accounts where id in ('$CA','$CB')" "$CA"
chk "authenticated B ve solo su buzón" "$(as authenticated $B) select string_agg(id::text,',') from public.communication_accounts where id in ('$CA','$CB')" "$CB"
chk "anon ve 0 buzones" "set role anon; select count(*) from public.communication_accounts where id in ('$CA','$CB')" 0
$PSQL -c "insert into public.admin_allowlist(user_id) values ('$A')"
chk "admin (allowlist) lee admin_events vía is_donexto_admin() (ruta /admin)" "$(as authenticated $A) select count(*)>0 from public.admin_events" t
chk "no admin lee 0 eventos" "$(as authenticated $B) select count(*) from public.admin_events" 0
chk "authenticated conserva permisos en tablas con políticas (donexto_preferences)" "select has_table_privilege('authenticated','public.donexto_preferences','insert')" t

$PSQL -c "delete from public.communication_accounts where id='$CA'"
chk "borrar buzón: 0 mensajes/hilos/trabajos huérfanos" "select (select count(*) from public.communication_messages where account_id='$CA')+(select count(*) from public.communication_threads where account_id='$CA')+(select count(*) from public.gmail_sync_jobs where account_id='$CA')" 0
cleanup; trap - EXIT
chk "datos reales intactos tras limpieza" "select count(*) from public.communication_messages" "$MSG0"

$PSQL -f $M/001_revoke_anon_authenticated.down.sql && ok "down aplicada"
AFTER=$(snap)
[ "$BEFORE" = "$AFTER" ] && ok "rollback: catálogo (restricciones, índices, políticas, GRANT) idéntico" || fail "rollback catálogo"
echo "TOTAL PASS=$pass"
