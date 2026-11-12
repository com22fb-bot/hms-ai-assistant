-- ARREGLO URGENTE e independiente del modelo destino P3 (23-oct-2026). PROPUESTA, NO APLICADA.
-- Quita GRANT excesivos (incl. TRUNCATE) a anon/authenticated en 8 tablas del motor con RLS y sin políticas.
-- Ningún cliente con anon/authenticated las usa: el frontend solo consulta admin_events y profiles; el backend usa service_role.
-- No cambia esquema, índices, restricciones ni datos.
begin;
revoke all on public.communication_messages, public.communication_threads, public.communication_tasks,
  public.attachments, public.ai_analysis, public.gmail_sync_jobs, public.system_incidents,
  public.case_reclassification_runs from anon, authenticated;
commit;
