-- 001 · A1: tablas legadas sin referencias en código
-- PREPARADA, NO APLICADA. Requiere confirmación de Héctor (lista A). Generada 23-oct-2026.
-- Verificado en producción (SELECT count(*)): todas estas tablas tienen 0 filas.
begin;
do $$ declare r text; n bigint; begin foreach r in array array['alerts','emails','user_workspaces','case_triage_backups','ops_r3_rows','ops_r3_rollback_report','ops_r3_operation'] loop if to_regclass('public.'||r) is not null then execute format('select count(*) from public.%I',r) into n; if n>0 then raise exception 'tabla % tiene % filas: abortado',r,n; end if; end if; end loop; end $$;
alter table public.tasks drop constraint if exists tasks_email_id_fkey;
drop function if exists public.ops_r3_rollback(uuid);
drop function if exists public.ops_r3_log(uuid, text, uuid, text, jsonb);
drop table if exists public.alerts;
drop table if exists public.emails;
drop table if exists public.user_workspaces;
drop table if exists public.case_triage_backups;
drop table if exists public.ops_r3_rows;
drop table if exists public.ops_r3_rollback_report;
drop table if exists public.ops_r3_operation;
commit;
