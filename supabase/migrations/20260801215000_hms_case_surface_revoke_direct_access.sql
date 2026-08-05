-- Sprint 4.10: no se permite leer ni modificar estas tablas directamente
-- con las funciones anon o authenticated de PostgREST.

revoke select, insert, update, delete, truncate, references, trigger
on table public.case_messages from anon, authenticated;

revoke select, insert, update, delete, truncate, references, trigger
on table public.case_participants from anon, authenticated;

revoke select, insert, update, delete, truncate, references, trigger
on table public.case_events from anon, authenticated;

revoke select, insert, update, delete, truncate, references, trigger
on table public.case_notifications from anon, authenticated;

revoke select, insert, update, delete, truncate, references, trigger
on table public.organizational_patterns from anon, authenticated;

revoke select, insert, update, delete, truncate, references, trigger
on table public.intelligent_cases from anon, authenticated;
