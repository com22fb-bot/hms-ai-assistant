#!/bin/bash
# Ensayo local del script de fase 1 (solo localhost). Uso: bash ensayo_local/run.sh
set -u; export PGPASSWORD=box; H="-h localhost -U box"; S=02_limpieza_fase1_PROPUESTA.sql
snap(){ psql $H -d rein -Atc "select string_agg(t||'='||n,' ' order by t) from (select 'acc' t,count(*) n from communication_accounts union all select 'ws',count(*) from workspaces union all select 'msg',count(*) from communication_messages union all select 'cases',count(*) from intelligent_cases union all select 'cred',count(*) from oauth_credentials union all select 'inc',count(*) from system_incidents union all select 'users',count(*) from auth.users union all select 'prof',count(*) from profiles) x"; }
third(){ psql $H -d rein -Atc "select md5(string_agg(md5(to_jsonb(a)::text),'' order by id)) from communication_accounts a where lower(email) not in ('hmcelinfo@gmail.com','hsalcidor@yahoo.com')"; }
reset(){ dropdb $H rein; createdb $H -T rein_base rein; }
ok=0; fail=0; chk(){ if [ "$1" = "$2" ]; then echo "PASS $3"; ok=$((ok+1)); else echo "FAIL $3 (esperado [$2] obtuvo [$1])"; fail=$((fail+1)); fi; }
reset; B=$(snap); T=$(third)
echo "== E1 ensayo confirmar=NO"; psql $H -d rein -q -v modo=huerfanas -v confirmar=NO -f $S 2>&1 | grep -o "ENSAYO.*Nada se borró." ; chk "$(snap)" "$B" "E1 ensayo no cambia nada"
echo "== E2 huerfanas confirmado"; psql $H -d rein -q -v modo=huerfanas -v confirmar=SI_BORRAR_2_CUENTAS_DE_PRUEBA -f $S >/tmp/e2.out 2>&1; tail -3 /tmp/e2.out | head -1
chk "$(snap)" "acc=5 cases=5 cred=5 inc=2 msg=25 prof=3 users=3 ws=5" "E2 huerfanas: borra W2,W3,WY2; conserva viva, mixta, tercero, WE"
chk "$(third)" "$T" "E2 terceros intactos (hash)"
chk "$(psql $H -d rein -Atc "select count(*) from communication_accounts where id='20000000-0000-0000-0000-00000000000d'")" "1" "E2 cuenta autorizada en ws mixto omitida"
chk "$(psql $H -d rein -Atc "select count(*) from system_incidents where account_id is null")" "1" "E2 incidente conservado y desvinculado"
echo "== E3 idempotente"; psql $H -d rein -q -v modo=huerfanas -v confirmar=SI_BORRAR_2_CUENTAS_DE_PRUEBA -f $S >/tmp/e3.out 2>&1; S3=$(snap); chk "$(grep -cE "\\| +[1-9][0-9]*$" /tmp/e3.out)" "0" "E3 segunda corrida borra 0 filas"
echo "== E4 completo"; psql $H -d rein -q -v modo=completo -v confirmar=SI_BORRAR_2_CUENTAS_DE_PRUEBA -f $S >/tmp/e4.out 2>&1
chk "$(snap)" "acc=3 cases=3 cred=3 inc=2 msg=15 prof=3 users=3 ws=3" "E4 completo: borra W1 y WY; usuarios/perfiles intactos"
chk "$(third)" "$T" "E4 terceros intactos"
chk "$(psql $H -d rein -Atc "select count(*) from donexto_preferences")" "2" "E4 preferencias conservadas (workspace→null)"
echo "== E5 guarda: miembro tercero en ws objetivo"; reset; psql $H -d rein -qc "insert into workspace_members(workspace_id,profile_id,role,status) values ('10000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-0000000000b1','viewer','invited')"; B=$(snap)
psql $H -d rein -q -v modo=huerfanas -v confirmar=SI_BORRAR_2_CUENTAS_DE_PRUEBA -f $S >/tmp/e5.out 2>&1; chk "$(psql $H -d rein -Atc "select count(*) from workspaces w join communication_accounts a on a.workspace_id=w.id where w.id='10000000-0000-0000-0000-000000000002'")" "1" "E5 ws con miembro tercero (invitado) se conserva con su cuenta"; chk "$(snap)" "acc=6 cases=6 cred=6 inc=2 msg=30 prof=3 users=3 ws=6" "E5 el resto sí se limpia"
echo "== E6 guarda: caso ajeno enlaza mensaje del alcance"; reset; psql $H -d rein -qc "insert into case_messages(case_id,message_id) select (select id from intelligent_cases where account_id='20000000-0000-0000-0000-000000000006'),(select id from communication_messages where account_id='20000000-0000-0000-0000-000000000002' limit 1 offset 2)"; B=$(snap)
psql $H -d rein -q -v modo=huerfanas -v confirmar=SI_BORRAR_2_CUENTAS_DE_PRUEBA -f $S >/tmp/e6.out 2>&1; grep -o "ABORT[^\"]*" /tmp/e6.out | head -1; chk "$(snap)" "$B" "E6 aborta sin cambios"
echo "== E7 guarda: umbral"; reset; B=$(snap); sed 's/15 max_acc/1 max_acc/' $S > /tmp/s7.sql; psql $H -d rein -q -v modo=huerfanas -v confirmar=SI_BORRAR_2_CUENTAS_DE_PRUEBA -f /tmp/s7.sql >/tmp/e7.out 2>&1; grep -o "ABORT[^\"]*" /tmp/e7.out|head -1; chk "$(snap)" "$B" "E7 umbral aborta sin cambios"
echo "== E8 guarda: job activo"; reset; psql $H -d rein -qc "update gmail_sync_jobs set status='running', heartbeat_at=now() where account_id='20000000-0000-0000-0000-000000000003'"; B=$(snap); psql $H -d rein -q -v modo=huerfanas -v confirmar=SI_BORRAR_2_CUENTAS_DE_PRUEBA -f $S >/tmp/e8.out 2>&1; grep -o "ABORT[^\"]*" /tmp/e8.out|head -1; chk "$(snap)" "$B" "E8 job activo aborta"
echo "TOTAL pass=$ok fail=$fail"
