-- 002 · A2: tablas legadas que aún aparecen en listas de limpieza (requiere C1 = PR #181 con 20261023_002 aplicada: borrado v2 sin tablas legadas; lo verifica la guardia de abajo)
-- PREPARADA, NO APLICADA. Requiere confirmación de Héctor (lista A). Generada 23-oct-2026.
-- Verificado en producción (SELECT count(*)): todas estas tablas tienen 0 filas.
begin;
-- Compatibilidad con PR #181: exige el borrado v2 (20261023_002_admin_purge_user_v2) y que NI admin_purge_targets
-- NI el cuerpo de admin_purge_user/_admin_purge_user_exec referencien las tablas que esta migración elimina.
do $$ declare v text; begin
  if to_regclass('public.admin_purge_targets') is null
     or to_regprocedure('public._admin_purge_user_exec(uuid,uuid)') is null
     or to_regprocedure('public._admin_purge_legacy_check(uuid)') is null then
    raise exception '002 requiere la migración 20261023_002_admin_purge_user_v2 (PR #181) aplicada antes (borrado v1 incompatible: usa public.users)';
  end if;
  select string_agg(distinct tbl, ',' order by tbl) into v from public.admin_purge_targets
   where tbl in ('notifications','users','reminders','tasks','audit_log','mail_accounts','alerts','emails','user_workspaces');
  if v is not null then raise exception '002 abortada: admin_purge_targets aún referencia %', v; end if;
  select string_agg(p.oid::regprocedure::text, ',') into v from pg_proc p
   where p.pronamespace = 'public'::regnamespace and p.proname in ('admin_purge_user', '_admin_purge_user_exec')
     and p.prosrc ~* 'public\.(notifications|users|reminders|tasks|audit_log|mail_accounts)([^a-z0-9_]|$)';
  if v is not null then raise exception '002 abortada: % aún referencia tablas que 002 elimina', v; end if;
end $$;
do $$ begin if to_regclass('public.alerts') is not null or to_regclass('public.emails') is not null then raise exception '002 requiere 001 aplicada'; end if; end $$;
do $$ declare r text; n bigint; begin foreach r in array array['notifications','users','reminders','tasks','audit_log','mail_accounts'] loop if to_regclass('public.'||r) is not null then execute format('select count(*) from public.%I',r) into n; if n>0 then raise exception 'tabla % tiene % filas: abortado',r,n; end if; end if; end loop; end $$;
drop table if exists public.notifications;
drop table if exists public.users;
drop table if exists public.reminders;
drop table if exists public.tasks;
drop table if exists public.audit_log;
drop table if exists public.mail_accounts;
commit;
