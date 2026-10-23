-- Revierte 004: deja índices, políticas y permisos como en producción al 23-oct-2026.
begin;
grant all on public.communication_tasks, public.communication_threads, public.attachments, public.ai_analysis,
  public.system_incidents, public.gmail_sync_jobs, public.communication_messages, public.case_reclassification_runs
  to anon, authenticated;
alter policy donexto_preferences_own on public.donexto_preferences
  using (profile_id = auth.uid()) with check (profile_id = auth.uid());
alter policy donexto_alert_rules_own on public.donexto_alert_rules
  using (profile_id = auth.uid()) with check (profile_id = auth.uid());
do $$ declare r record; begin
  for r in select indexrelid::regclass as i from pg_index x join pg_class c on c.oid=x.indexrelid
            where c.relnamespace='public'::regnamespace and c.relname like 'ix\_fk\_%' loop
    execute format('drop index %s', r.i);
  end loop;
end $$;
commit;
