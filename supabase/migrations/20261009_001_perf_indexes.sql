-- Rendimiento: índices que faltaban (auditoría del 7 oct).
-- Hilos: se buscan mensajes por thread_id al abrir un hilo y al agrupar casos.
create index if not exists idx_messages_thread_received
  on public.communication_messages (thread_id, received_at desc);
-- Notificaciones por caso (borrado/lectura de avisos de un caso).
create index if not exists idx_case_notifications_case
  on public.case_notifications (case_id);
-- Llaves foráneas sin índice que se usan en el dashboard y en los avisos (advisor de Supabase).
create index if not exists idx_case_notifications_event on public.case_notifications (event_id);
create index if not exists idx_case_events_message on public.case_events (message_id);
create index if not exists idx_attachments_message on public.attachments (message_id);
create index if not exists idx_intelligent_cases_primary_thread on public.intelligent_cases (primary_thread_id);
create index if not exists idx_hms_notifications_workspace on public.hms_notifications (workspace_id);
create index if not exists idx_hms_notifications_case on public.hms_notifications (case_id);
create index if not exists idx_hms_notifications_message on public.hms_notifications (message_id);
create index if not exists idx_user_workspaces_user on public.user_workspaces (user_id);
