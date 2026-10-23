\set ON_ERROR_STOP on
-- Usuarios: A (a borrar, espacio propio), B (comparte espacio S con A), ADM (admin).
insert into auth.users(id,email) values
 ('00000000-0000-0000-0000-00000000000a','a@test'),('00000000-0000-0000-0000-00000000000b','b@test'),
 ('00000000-0000-0000-0000-0000000000ad','adm@test');
insert into public.profiles select id,email from auth.users;
insert into public.users select id,email from auth.users;
insert into public.admin_allowlist values ('00000000-0000-0000-0000-0000000000ad');
insert into public.notifications(user_id) values ('00000000-0000-0000-0000-00000000000a'),('00000000-0000-0000-0000-00000000000b');
insert into public.workspaces(id,owner_profile_id) values
 ('10000000-0000-0000-0000-00000000000a','00000000-0000-0000-0000-00000000000a'),
 ('10000000-0000-0000-0000-00000000000b','00000000-0000-0000-0000-00000000000b'),
 ('10000000-0000-0000-0000-0000000000cc','00000000-0000-0000-0000-00000000000b');
insert into public.workspace_members values
 ('10000000-0000-0000-0000-00000000000a','00000000-0000-0000-0000-00000000000a'),
 ('10000000-0000-0000-0000-00000000000b','00000000-0000-0000-0000-00000000000b'),
 ('10000000-0000-0000-0000-0000000000cc','00000000-0000-0000-0000-00000000000a'),
 ('10000000-0000-0000-0000-0000000000cc','00000000-0000-0000-0000-00000000000b');
insert into public.communication_accounts(id,workspace_id,connected_by_profile_id) values
 ('20000000-0000-0000-0000-00000000000a','10000000-0000-0000-0000-00000000000a','00000000-0000-0000-0000-00000000000a'),
 ('20000000-0000-0000-0000-00000000000b','10000000-0000-0000-0000-00000000000b','00000000-0000-0000-0000-00000000000b');
insert into public.oauth_credentials(account_id) select id from public.communication_accounts;
insert into public.communication_threads(id,account_id) values
 ('30000000-0000-0000-0000-00000000000a','20000000-0000-0000-0000-00000000000a'),
 ('30000000-0000-0000-0000-00000000000b','20000000-0000-0000-0000-00000000000b');
insert into public.communication_messages(account_id,thread_id)
 select a, t from (values ('20000000-0000-0000-0000-00000000000a'::uuid,'30000000-0000-0000-0000-00000000000a'::uuid),
                          ('20000000-0000-0000-0000-00000000000b'::uuid,'30000000-0000-0000-0000-00000000000b'::uuid)) v(a,t), generate_series(1,3);
insert into public.ai_analysis(message_id) select id from public.communication_messages;
insert into public.intelligent_cases(workspace_id,account_id) select workspace_id,id from public.communication_accounts;
insert into public.case_messages(case_id,message_id) select c.id,m.id from public.intelligent_cases c join public.communication_messages m on m.account_id=c.account_id;
insert into public.case_events(case_id,workspace_id) select id,workspace_id from public.intelligent_cases;
insert into public.system_incidents(workspace_id,account_id) select workspace_id,id from public.communication_accounts;
insert into public.mail_accounts(user_id) select id from auth.users where email<>'adm@test';
insert into public.emails(user_id,mail_account_id) select user_id,id from public.mail_accounts;
insert into public.tasks(user_id) select id from auth.users where email<>'adm@test';
insert into public.audit_log(user_id) select id from auth.users;

-- 1) Admin protegido.
do $$ begin
  perform public.admin_purge_user('00000000-0000-0000-0000-0000000000ad');
  raise exception 'FALLA: borró a un admin';
exception when others then
  if sqlerrm like 'FALLA%' then raise; end if;
end $$;

-- 2) Borrado de A.
select public.admin_purge_user('00000000-0000-0000-0000-00000000000a') as result \gset
\echo :result

do $$
declare a uuid := '00000000-0000-0000-0000-00000000000a'; b uuid := '00000000-0000-0000-0000-00000000000b';
begin
  assert not exists (select 1 from auth.users where id=a), 'auth.users A';
  assert not exists (select 1 from public.profiles where id=a), 'profile A';
  assert not exists (select 1 from public.communication_accounts where workspace_id='10000000-0000-0000-0000-00000000000a'), 'buzón A';
  assert (select count(*) from public.communication_messages) = 3, 'solo quedan mensajes de B';
  assert (select count(*) from public.oauth_credentials) = 1, 'credenciales';
  assert (select count(*) from public.intelligent_cases) = 1, 'casos';
  assert (select count(*) from public.ai_analysis) = 3, 'clasificaciones';
  assert (select count(*) from public.system_incidents) = 1, 'incidentes';
  assert not exists (select 1 from public.emails where user_id=a), 'emails A';
  assert not exists (select 1 from public.audit_log where user_id=a), 'audit A';
  assert not exists (select 1 from public.notifications where user_id=a), 'notifications A';
  assert not exists (select 1 from public.workspaces where id='10000000-0000-0000-0000-00000000000a'), 'espacio propio';
  assert exists (select 1 from public.workspaces where id='10000000-0000-0000-0000-0000000000cc'), 'espacio compartido se conserva';
  assert not exists (select 1 from public.workspace_members where profile_id=a), 'membresías A';
  assert exists (select 1 from auth.users where id=b) and (select count(*) from public.emails where user_id=b)=1, 'B intacto';
  assert (select count(*) from public.admin_events where meta->>'kind'='user_purge') = 1, 'bitácora';
  assert (select meta::text from public.admin_events where meta->>'kind'='user_purge') not like '%a@test%', 'sin PII';
  assert (select meta::text from public.admin_events where meta->>'kind'='user_purge') not like '%00000000-0000-0000-0000-00000000000a%', 'sin ID';
  assert ((select meta from public.admin_events where meta->>'kind'='user_purge')->'counts'->>'communication_messages')::int = 3, 'conteo mensajes';
end $$;

-- 3) Transaccional: si algo falla, no se borra nada.
create function public.fail_purge() returns trigger language plpgsql as $$ begin raise exception 'forzado'; end $$;
create trigger t_fail before delete on public.profiles for each row execute function public.fail_purge();
do $$ begin
  perform public.admin_purge_user('00000000-0000-0000-0000-00000000000b');
  raise exception 'FALLA: no abortó';
exception when others then
  if sqlerrm like 'FALLA%' then raise; end if;
end $$;
do $$ begin
  assert (select count(*) from public.communication_messages) = 3, 'rollback mensajes';
  assert exists (select 1 from auth.users where id='00000000-0000-0000-0000-00000000000b'), 'rollback auth';
end $$;

-- 4) Permisos: anon/authenticated no pueden ejecutarla.
do $$ begin
  assert not has_function_privilege('anon', 'public.admin_purge_user(uuid)', 'execute'), 'anon';
  assert not has_function_privilege('authenticated', 'public.admin_purge_user(uuid)', 'execute'), 'authenticated';
  assert has_function_privilege('service_role', 'public.admin_purge_user(uuid)', 'execute'), 'service_role';
end $$;

-- 5) Alta: usuario nuevo queda como prueba de 3 días.
insert into auth.users(id,email) values ('00000000-0000-0000-0000-0000000000ee','nuevo@test');
do $$ begin
  assert (select is_test and status='trialing' and trial_ends_at - trial_started_at = interval '3 days'
          from public.account_plans where user_id='00000000-0000-0000-0000-0000000000ee'), 'plan de prueba';
end $$;
\echo 'admin_purge_user: TODAS LAS PRUEBAS PASARON'
