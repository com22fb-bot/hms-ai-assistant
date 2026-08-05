-- Sprint 4.10: las tablas operativas de casos quedan cerradas a acceso directo.
-- El backend conserva acceso mediante service_role y aplica el contexto de workspace.

alter table public.case_messages enable row level security;
alter table public.case_participants enable row level security;
alter table public.case_events enable row level security;
alter table public.case_notifications enable row level security;
alter table public.organizational_patterns enable row level security;
alter table public.intelligent_cases enable row level security;
