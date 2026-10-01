-- Bandeja de mensajes del formulario público (donexto.com).
-- Solo el backend con service role lee y escribe. No hay políticas para
-- anon ni authenticated: con RLS activo, PostgREST les niega el acceso.

create table if not exists public.contact_messages (
  id uuid primary key,
  name text not null default '',
  email text not null,
  country text not null default '',
  message text not null,
  language text not null default '',
  subject text not null default '',
  status text not null default 'nuevo'
    check (status in ('nuevo', 'borrador listo', 'respondido', 'archivado')),
  ip_hash text,
  draft_body text,
  draft_error text,
  reply_body text,
  replied_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_contact_messages_created
  on public.contact_messages (created_at desc);

create index if not exists idx_contact_messages_status
  on public.contact_messages (status, created_at desc);

alter table public.contact_messages enable row level security;
alter table public.contact_messages force row level security;

revoke all on table public.contact_messages from public;
revoke all on table public.contact_messages from anon;
revoke all on table public.contact_messages from authenticated;
grant all on table public.contact_messages to service_role;

comment on table public.contact_messages is
  'Mensajes del formulario público. Solo el backend (service role) lee y escribe.';
