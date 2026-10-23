-- 002 · A2: tablas legadas que aún aparecen en listas de limpieza (requiere C1: quitarlas de admin_ops._WORKSPACE_CLEANUP_TABLES, admin_purge_targets del #181 y system.py mail_accounts)
-- PREPARADA, NO APLICADA. Requiere confirmación de Héctor (lista A). Generada 23-oct-2026.
-- Verificado en producción (SELECT count(*)): todas estas tablas tienen 0 filas.
begin;
do $$ begin if to_regclass('public.alerts') is not null or to_regclass('public.emails') is not null then raise exception '002 requiere 001 aplicada'; end if; end $$;
do $$ declare r text; n bigint; begin foreach r in array array['notifications','users','reminders','tasks','audit_log','mail_accounts'] loop if to_regclass('public.'||r) is not null then execute format('select count(*) from public.%I',r) into n; if n>0 then raise exception 'tabla % tiene % filas: abortado',r,n; end if; end if; end loop; end $$;
drop table if exists public.notifications;
drop table if exists public.users;
drop table if exists public.reminders;
drop table if exists public.tasks;
drop table if exists public.audit_log;
drop table if exists public.mail_accounts;
commit;
