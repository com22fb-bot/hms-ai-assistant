-- 004 · Advisors de Supabase (23-oct-2026). PROPUESTA, NO APLICADA. Requiere 001–003.
-- (a) índice para cada FK sin índice (unindexed_foreign_keys), (b) políticas con auth.uid() por fila (auth_rls_initplan),
-- (c) higiene de permisos: quitar GRANT a anon/authenticated en tablas con RLS sin políticas (el backend usa service_role).
-- No toca datos. No cambia is_donexto_admin(): lo usan las políticas de admin_events (ver docs).
begin;
do $$ begin
  if to_regclass('public.tasks') is not null then raise exception '004 requiere 001/002 aplicadas'; end if;
end $$;
do $$ declare r record; n text; begin
  for r in select c.conrelid::regclass as t, c.conrelid, a.attname
             from pg_constraint c join pg_attribute a on a.attrelid=c.conrelid and a.attnum=c.conkey[1]
            where c.connamespace='public'::regnamespace and c.contype='f'
              and not exists (select 1 from pg_index i where i.indrelid=c.conrelid and i.indkey[0]=c.conkey[1]) loop
    n := left('ix_fk_'||(select relname from pg_class where oid=r.conrelid)||'_'||r.attname, 63);
    execute format('create index if not exists %I on %s (%I)', n, r.t, r.attname);
  end loop;
end $$;
alter policy donexto_preferences_own on public.donexto_preferences
  using (profile_id = (select auth.uid())) with check (profile_id = (select auth.uid()));
alter policy donexto_alert_rules_own on public.donexto_alert_rules
  using (profile_id = (select auth.uid())) with check (profile_id = (select auth.uid()));
revoke all on public.communication_tasks, public.communication_threads, public.attachments, public.ai_analysis,
  public.system_incidents, public.gmail_sync_jobs, public.communication_messages, public.case_reclassification_runs
  from anon, authenticated;
commit;
