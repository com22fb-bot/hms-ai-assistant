begin;
grant all on public.communication_messages, public.communication_threads, public.communication_tasks,
  public.attachments, public.ai_analysis, public.gmail_sync_jobs, public.system_incidents,
  public.case_reclassification_runs to anon, authenticated;
commit;
