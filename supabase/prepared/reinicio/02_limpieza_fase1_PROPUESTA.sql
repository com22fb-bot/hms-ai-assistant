-- REINICIO DE DATOS DE PRUEBA · FASE 1 (PROPUESTA, NO EJECUTADA EN PRODUCCIÓN)
-- Borra SOLO cuentas de buzón de los 2 correos autorizados y los workspaces EXCLUSIVOS de ellos.
-- No toca auth.users, auth.identities ni profiles (eso es la fase 2, aparte).
-- No usa TRUNCATE ni CASCADE explícito; borra hijos antes que padres; idempotente (2.ª corrida = 0 filas).
-- Uso: psql -v ON_ERROR_STOP=1 -v modo=huerfanas -v confirmar=NO -f este_archivo   (NO = ensayo con ROLLBACK)
--      psql ... -v confirmar=SI_BORRAR_2_CUENTAS_DE_PRUEBA       (solo con aprobación de Héctor)
\set ON_ERROR_STOP 1
begin;
set local lock_timeout = '5s';
set local statement_timeout = '120s';
select set_config('reinicio.confirmar', :'confirmar', true);
-- Modo: 'huerfanas' = solo cuentas en workspaces sin miembros vivos; 'completo' = también la cuenta viva y su workspace.
select set_config('reinicio.modo', :'modo', true);

create temp table r_params on commit drop as select array['hmcelinfo@gmail.com','hsalcidor@yahoo.com']::text[] emails,
  -- umbrales (dry-run del 12-oct: 12 cuentas, 7,082 mensajes, 6,690 hilos, 11 workspaces)
  15 max_acc, 9000 max_msg, 8000 max_thr, 15 max_ws, 2 max_users;
create temp table r_users on commit drop as select u.id from auth.users u, r_params p where lower(u.email)=any(p.emails);
create temp table r_acc_all on commit drop as select a.id, a.workspace_id from public.communication_accounts a, r_params p where lower(a.email)=any(p.emails);
create temp table r_ws on commit drop as select w.id from public.workspaces w where w.id in (select workspace_id from r_acc_all)
   and not exists (select 1 from public.communication_accounts a, r_params p where a.workspace_id=w.id and lower(coalesce(a.email,''))<>all(p.emails))
   and not exists (select 1 from public.workspace_members m where m.workspace_id=w.id and m.profile_id not in (select id from r_users))
   and (current_setting('reinicio.modo')='completo'
        or not exists (select 1 from public.workspace_members m where m.workspace_id=w.id and m.status='active' and m.deleted_at is null));
-- Solo cuentas cuyo workspace es exclusivo; las de workspaces mixtos (p. ej. 24c2163d) se OMITEN y se reportan.
create temp table r_acc on commit drop as select id from r_acc_all where workspace_id in (select id from r_ws);
create temp table r_cases on commit drop as select id from public.intelligent_cases where account_id in (select id from r_acc) or workspace_id in (select id from r_ws);
create temp table r_runs on commit drop as select id from public.case_reclassification_runs where account_id in (select id from r_acc) or workspace_id in (select id from r_ws);
create temp table r_notif on commit drop as select id from public.hms_notifications where account_id in (select id from r_acc) or workspace_id in (select id from r_ws);
create temp table r_terceros on commit drop as select
  (select md5(coalesce(string_agg(md5(to_jsonb(a)::text),'' order by a.id),'')) from public.communication_accounts a, r_params q where lower(coalesce(a.email,''))<>all(q.emails)) h,
  (select count(*) from public.communication_messages where account_id not in (select id from r_acc_all)) m,
  (select count(*) from public.workspaces where id not in (select id from r_ws)) w;
create temp table r_log (paso int, tabla text, filas bigint) on commit drop;

-- ===== GUARDAS (abortan toda la transacción) =====
do $$
declare p record; n bigint;
begin
  select * into p from r_params;
  if (select count(*) from r_users) > p.max_users then raise exception 'ABORT: más usuarios de los esperados'; end if;
  if (select count(*) from r_acc) > p.max_acc then raise exception 'ABORT: cuentas % > %', (select count(*) from r_acc), p.max_acc; end if;
  if (select count(*) from r_ws) > p.max_ws then raise exception 'ABORT: workspaces > umbral'; end if;
  select count(*) into n from public.communication_messages where account_id in (select id from r_acc);
  if n > p.max_msg then raise exception 'ABORT: mensajes % > %', n, p.max_msg; end if;
  if (select count(*) from public.communication_threads where account_id in (select id from r_acc)) > p.max_thr then raise exception 'ABORT: hilos > umbral'; end if;
  -- ninguna cuenta a borrar puede tener correo fuera de la lista
  if exists (select 1 from public.communication_accounts a, r_params q where a.id in (select id from r_acc) and lower(coalesce(a.email,''))<>all(q.emails)) then raise exception 'ABORT: cuenta ajena en el alcance'; end if;
  -- ningún workspace a borrar puede tener cuentas o miembros de terceros
  if exists (select 1 from public.communication_accounts a, r_params q where a.workspace_id in (select id from r_ws) and lower(coalesce(a.email,''))<>all(q.emails)) then raise exception 'ABORT: workspace con cuenta de tercero'; end if;
  if exists (select 1 from public.workspace_members m where m.workspace_id in (select id from r_ws) and m.profile_id not in (select id from r_users)) then raise exception 'ABORT: workspace con miembro de tercero'; end if;
  -- relaciones ambiguas: casos del alcance que enlazan mensajes de cuentas fuera del alcance, o al revés
  if exists (select 1 from public.case_messages cm join public.communication_messages x on x.id=cm.message_id where cm.case_id in (select id from r_cases) and x.account_id not in (select id from r_acc)) then raise exception 'ABORT: caso del alcance enlaza mensajes ajenos'; end if;
  if exists (select 1 from public.case_messages cm join public.communication_messages x on x.id=cm.message_id where x.account_id in (select id from r_acc) and cm.case_id not in (select id from r_cases)) then raise exception 'ABORT: caso ajeno enlaza mensajes del alcance'; end if;
  if exists (select 1 from public.intelligent_cases c where c.id in (select id from r_cases) and c.workspace_id not in (select id from r_ws) and c.account_id not in (select id from r_acc)) then raise exception 'ABORT: caso ambiguo'; end if;
  -- sincronización en curso: no borrar con jobs vivos
  if exists (select 1 from public.gmail_sync_jobs j where j.account_id in (select id from r_acc) and j.status in ('running','queued','pending') and coalesce(j.heartbeat_at, j.updated_at) > now() - interval '15 minutes') then raise exception 'ABORT: job de sync activo'; end if;
end $$;

-- ===== PRE-CHECK (para el registro) =====
select 'pre' fase, (select count(*) from r_users) usuarios, (select count(*) from r_acc) cuentas, (select count(*) from r_acc_all)-(select count(*) from r_acc) cuentas_omitidas_ws_mixto,
       (select count(*) from r_ws) workspaces, (select count(*) from r_cases) casos;

-- ===== BORRADO EN ORDEN DE DEPENDENCIAS (hijos primero) =====
with d as (delete from public.push_delivery_log where notification_id in (select id from r_notif) returning 1) insert into r_log select 1,'push_delivery_log',count(*) from d;
with d as (delete from public.hms_notifications where id in (select id from r_notif) returning 1) insert into r_log select 2,'hms_notifications',count(*) from d;
with d as (delete from public.case_notifications where case_id in (select id from r_cases) or workspace_id in (select id from r_ws) returning 1) insert into r_log select 3,'case_notifications',count(*) from d;
with d as (delete from public.case_events where case_id in (select id from r_cases) or workspace_id in (select id from r_ws) returning 1) insert into r_log select 4,'case_events',count(*) from d;
with d as (delete from public.case_participants where case_id in (select id from r_cases) returning 1) insert into r_log select 5,'case_participants',count(*) from d;
with d as (delete from public.case_messages where case_id in (select id from r_cases) returning 1) insert into r_log select 6,'case_messages',count(*) from d;
with d as (delete from public.case_triage_backups where case_id in (select id from r_cases) or run_id in (select id from r_runs) returning 1) insert into r_log select 7,'case_triage_backups',count(*) from d;
with d as (delete from public.reclassification_backup_rows where run_id in (select id from r_runs) returning 1) insert into r_log select 8,'reclassification_backup_rows',count(*) from d;
with d as (delete from public.case_reclassification_runs where id in (select id from r_runs) returning 1) insert into r_log select 9,'case_reclassification_runs',count(*) from d;
with d as (delete from public.intelligent_cases where id in (select id from r_cases) returning 1) insert into r_log select 10,'intelligent_cases',count(*) from d;
with d as (delete from public.message_watch_matches where rule_id in (select id from public.message_watch_rules where account_id in (select id from r_acc) or workspace_id in (select id from r_ws)) or message_id in (select id from public.communication_messages where account_id in (select id from r_acc)) returning 1) insert into r_log select 11,'message_watch_matches',count(*) from d;
with d as (delete from public.message_watch_rules where account_id in (select id from r_acc) or workspace_id in (select id from r_ws) returning 1) insert into r_log select 12,'message_watch_rules',count(*) from d;
-- system_incidents se CONSERVAN (FK SET NULL): se desvinculan explícitamente para dejar rastro
with d as (update public.system_incidents set account_id=null where account_id in (select id from r_acc) returning 1) insert into r_log select 13,'system_incidents(account→null)',count(*) from d;
with d as (update public.system_incidents set workspace_id=null where workspace_id in (select id from r_ws) returning 1) insert into r_log select 14,'system_incidents(ws→null)',count(*) from d;
with d as (update public.system_incidents set sync_job_id=null where sync_job_id in (select id from public.gmail_sync_jobs where account_id in (select id from r_acc) or workspace_id in (select id from r_ws)) returning 1) insert into r_log select 15,'system_incidents(job→null)',count(*) from d;
with d as (delete from public.gmail_sync_jobs where account_id in (select id from r_acc) or workspace_id in (select id from r_ws) returning 1) insert into r_log select 16,'gmail_sync_jobs',count(*) from d;
with d as (delete from public.message_classification_rules where account_id in (select id from r_acc) or workspace_id in (select id from r_ws) returning 1) insert into r_log select 17,'message_classification_rules',count(*) from d;
with d as (delete from public.communication_messages where account_id in (select id from r_acc) returning 1) insert into r_log select 18,'communication_messages',count(*) from d;
with d as (delete from public.communication_threads where account_id in (select id from r_acc) returning 1) insert into r_log select 19,'communication_threads',count(*) from d;
with d as (delete from public.oauth_credentials where account_id in (select id from r_acc) returning 1) insert into r_log select 20,'oauth_credentials',count(*) from d;
with d as (delete from public.communication_accounts where id in (select id from r_acc) returning 1) insert into r_log select 21,'communication_accounts',count(*) from d;
with d as (delete from public.organizational_patterns where workspace_id in (select id from r_ws) returning 1) insert into r_log select 22,'organizational_patterns',count(*) from d;
with d as (delete from public.oauth_states where workspace_id in (select id from r_ws) returning 1) insert into r_log select 23,'oauth_states',count(*) from d;
with d as (delete from public.push_subscriptions where workspace_id in (select id from r_ws) returning 1) insert into r_log select 24,'push_subscriptions',count(*) from d;
-- preferencias: se desvincula el workspace (FK SET NULL); el perfil y su preferencia se tratan en fase 2
with d as (update public.donexto_preferences set workspace_id=null where workspace_id in (select id from r_ws) returning 1) insert into r_log select 25,'donexto_preferences(ws→null)',count(*) from d;
with d as (delete from public.workspace_members where workspace_id in (select id from r_ws) returning 1) insert into r_log select 26,'workspace_members',count(*) from d;
with d as (delete from public.workspaces where id in (select id from r_ws) returning 1) insert into r_log select 27,'workspaces',count(*) from d;

select paso, tabla, filas from r_log order by paso;

-- ===== POST-CHECK =====
do $$ begin
  if exists (select 1 from public.communication_accounts where id in (select id from r_acc)) then raise exception 'POST: quedan cuentas'; end if;
  if exists (select 1 from public.communication_messages where account_id in (select id from r_acc)) then raise exception 'POST: quedan mensajes'; end if;
  if exists (select 1 from public.workspaces where id in (select id from r_ws)) then raise exception 'POST: quedan workspaces'; end if;
  if exists (select 1 from public.communication_accounts a where not exists (select 1 from public.workspaces w where w.id=a.workspace_id)) then raise exception 'POST: cuenta sin workspace'; end if;
  -- nada de terceros cambió: mismas cuentas ajenas que antes
  if (select h from r_terceros) <> (select md5(coalesce(string_agg(md5(to_jsonb(a)::text),'' order by a.id),'')) from public.communication_accounts a, r_params q where lower(coalesce(a.email,''))<>all(q.emails))
     or (select m from r_terceros) <> (select count(*) from public.communication_messages where account_id not in (select id from r_acc_all))
     or (select w from r_terceros) <> (select count(*) from public.workspaces where id not in (select id from r_ws)) then raise exception 'POST: cambió algo de terceros'; end if;
  if current_setting('reinicio.confirmar') <> 'SI_BORRAR_2_CUENTAS_DE_PRUEBA' then
    raise exception 'ENSAYO: confirmar=% → se revierte todo (ROLLBACK). Nada se borró.', current_setting('reinicio.confirmar');
  end if;
end $$;
commit;
