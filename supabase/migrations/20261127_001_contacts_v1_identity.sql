-- CONTACTS_V1 · F1 · Modelo canónico de identidad y participantes.
-- Diseño: docs/auditorias/contactos/F0_F1.md (auditoría sobre 9ee269e).
-- Rollback: supabase/rollbacks/20261127_001_contacts_v1_identity_rollback.sql
--
-- Solo crea tablas NUEVAS; no altera ninguna tabla existente. Nada en el código
-- las escribe mientras CONTACTS_V1_ENABLED=false (valor por defecto) y en F1 el
-- registro NO está enchufado a la importación ni al motor de casos.
--
--   message_participants  DERIVADO: participantes por mensaje (reconstruible desde
--                         communication_messages). Guarda también los no confiables
--                         (ambiguous/invalid) para auditoría, sin address_norm.
--   contact_addresses     DERIVADO: identidad consolidada por workspace + dirección
--                         normalizada. Las estadísticas las calcula solo el
--                         constructor idempotente (F3); F1 no las escribe.
--   own_address_aliases   Alias propios que NO son buzones conectados
--                         (detected → confirmed/rejected solo con decisión).
--
-- Seguridad: RLS activa y sin acceso anon/authenticated (patrón de
-- 20260801214500_hms_case_surface_enable_rls.sql); el backend usa service_role.

-- Formato de address_norm (lo produce app/services/contact_identity.py):
-- minúsculas, sin espacios ni separadores, dominio ASCII (IDNA) con al menos un punto.

create table if not exists public.message_participants (
  id               bigint generated always as identity primary key,
  message_id       uuid not null references public.communication_messages(id) on delete cascade,
  workspace_id     uuid not null references public.workspaces(id) on delete cascade,
  account_id       uuid not null references public.communication_accounts(id) on delete cascade,
  role             text not null check (role in ('from', 'sender', 'reply_to', 'to', 'cc', 'bcc')),
  position         smallint not null check (position between 0 and 999),
  address_original text not null check (char_length(address_original) <= 998),
  address_norm     text check (
    address_norm is null or (
      address_norm = lower(address_norm)
      and char_length(address_norm) <= 254
      and address_norm ~ '^[^@[:space:]<>,;"\\]+@[a-z0-9-]+(\.[a-z0-9-]+)+$'
    )
  ),
  display_name     text check (display_name is null or char_length(display_name) <= 300),
  parse_status     text not null check (parse_status in ('ok', 'ambiguous', 'invalid')),
  parse_reason     text not null default 'ok' check (char_length(parse_reason) <= 64),
  source           text not null check (source in ('gmail_api', 'microsoft_graph', 'imap', 'gmail_imap',
                                                   'stored_sender', 'stored_recipients', 'fixture')),
  provider         text check (provider is null or char_length(provider) <= 32),
  direction        text not null check (direction in ('inbound', 'outbound', 'draft', 'system')),
  occurred_at      timestamptz not null,
  is_own           boolean not null default false,
  flags            text[] not null default '{}' check (cardinality(flags) <= 8),
  created_at       timestamptz not null default timezone('utc', now()),
  updated_at       timestamptz not null default timezone('utc', now()),
  -- Solo una identidad confiable lleva dirección normalizada (no se inventan direcciones).
  constraint message_participants_norm_iff_ok check ((parse_status = 'ok') = (address_norm is not null)),
  -- Una dirección no confiable nunca se marca como propia.
  constraint message_participants_own_requires_ok check (not is_own or parse_status = 'ok'),
  constraint message_participants_slot_key unique (message_id, role, position)
);
-- Duplicados controlados: la misma dirección no se repite en el mismo rol del mismo mensaje.
create unique index if not exists ux_message_participants_role_address
  on public.message_participants (message_id, role, address_norm) where address_norm is not null;
create index if not exists ix_message_participants_ws_addr_time
  on public.message_participants (workspace_id, address_norm, occurred_at desc);
create index if not exists ix_message_participants_ws_dir_time
  on public.message_participants (workspace_id, direction, occurred_at desc)
  where not is_own and address_norm is not null;
create index if not exists ix_message_participants_account on public.message_participants (account_id);

-- Integridad entre mensaje, cuenta y workspace (aislamiento): el mensaje debe ser de
-- esa cuenta y la cuenta de ese workspace. Se usa un trigger para no alterar
-- communication_accounts con una clave compuesta nueva.
create or replace function public.contacts_v1_participant_guard()
returns trigger
language plpgsql
set search_path = public, pg_temp
as $$
begin
  if not exists (
    select 1
    from public.communication_messages m
    join public.communication_accounts a on a.id = m.account_id
    where m.id = new.message_id
      and a.id = new.account_id
      and a.workspace_id = new.workspace_id
  ) then
    raise exception 'contacts_v1: participante inconsistente con mensaje/cuenta/workspace'
      using errcode = '23503';
  end if;
  return new;
end;
$$;
revoke all on function public.contacts_v1_participant_guard() from public;
do $$ begin
  if exists (select 1 from pg_roles where rolname = 'anon') then
    revoke all on function public.contacts_v1_participant_guard() from anon, authenticated;
  end if;
end $$;

drop trigger if exists trg_contacts_v1_participant_guard on public.message_participants;
create trigger trg_contacts_v1_participant_guard
before insert or update of message_id, account_id, workspace_id on public.message_participants
for each row execute function public.contacts_v1_participant_guard();

drop trigger if exists trg_message_participants_updated_at on public.message_participants;
create trigger trg_message_participants_updated_at
before update on public.message_participants
for each row execute function public.hms_touch_updated_at();

create table if not exists public.contact_addresses (
  id                 uuid primary key default gen_random_uuid(),
  workspace_id       uuid not null references public.workspaces(id) on delete cascade,
  address_norm       text not null check (
    address_norm = lower(address_norm)
    and char_length(address_norm) <= 254
    and address_norm ~ '^[^@[:space:]<>,;"\\]+@[a-z0-9-]+(\.[a-z0-9-]+)+$'
  ),
  domain             text generated always as (split_part(address_norm, '@', 2)) stored,
  -- Descriptivo, NO autoritativo: variantes originales y nombres visibles observados.
  originals          text[] not null default '{}' check (cardinality(originals) <= 10),
  display_names      jsonb not null default '{}'::jsonb check (jsonb_typeof(display_names) = 'object'),
  entity_kind        text not null default 'unknown'
                     check (entity_kind in ('person', 'organization', 'automated', 'unknown')),
  entity_evidence    jsonb not null default '{}'::jsonb check (jsonb_typeof(entity_evidence) = 'object'),
  -- DERIVADO por el constructor idempotente (F3) desde message_participants; nunca manual.
  received_count     integer not null default 0 check (received_count >= 0),
  sent_count         integer not null default 0 check (sent_count >= 0),
  interactions       integer not null default 0 check (interactions >= 0),
  conversations      integer not null default 0 check (conversations >= 0),
  first_at           timestamptz,
  last_at            timestamptz,
  last_received_at   timestamptz,
  last_sent_at       timestamptz,
  accounts           jsonb not null default '[]'::jsonb check (jsonb_typeof(accounts) = 'array'),
  suggestion_score   smallint not null default 0 check (suggestion_score between 0 and 100),
  suggestion_reasons jsonb not null default '[]'::jsonb check (jsonb_typeof(suggestion_reasons) = 'array'),
  stats_version      integer not null default 0 check (stats_version >= 0),
  stats_rebuilt_at   timestamptz,
  created_at         timestamptz not null default timezone('utc', now()),
  updated_at         timestamptz not null default timezone('utc', now()),
  constraint contact_addresses_workspace_address_key unique (workspace_id, address_norm),
  constraint contact_addresses_time_order check (first_at is null or last_at is null or first_at <= last_at)
);
create index if not exists ix_contact_addresses_ws_suggest
  on public.contact_addresses (workspace_id, suggestion_score desc, last_at desc nulls last);
create index if not exists ix_contact_addresses_ws_domain
  on public.contact_addresses (workspace_id, domain);

drop trigger if exists trg_contact_addresses_updated_at on public.contact_addresses;
create trigger trg_contact_addresses_updated_at
before update on public.contact_addresses
for each row execute function public.hms_touch_updated_at();

create table if not exists public.own_address_aliases (
  workspace_id  uuid not null references public.workspaces(id) on delete cascade,
  address_norm  text not null check (
    address_norm = lower(address_norm)
    and char_length(address_norm) <= 254
    and address_norm ~ '^[^@[:space:]<>,;"\\]+@[a-z0-9-]+(\.[a-z0-9-]+)+$'
  ),
  status        text not null check (status in ('detected', 'confirmed', 'rejected')),
  evidence      jsonb not null default '{}'::jsonb check (jsonb_typeof(evidence) = 'object'),
  detected_at   timestamptz not null default timezone('utc', now()),
  decided_by    uuid references public.profiles(id) on delete set null,
  decided_at    timestamptz,
  created_at    timestamptz not null default timezone('utc', now()),
  updated_at    timestamptz not null default timezone('utc', now()),
  primary key (workspace_id, address_norm),
  -- 'detected' es solo sugerencia: confirmar o rechazar exige una decisión con fecha.
  constraint own_address_aliases_decision check ((status = 'detected') = (decided_at is null))
);

drop trigger if exists trg_own_address_aliases_updated_at on public.own_address_aliases;
create trigger trg_own_address_aliases_updated_at
before update on public.own_address_aliases
for each row execute function public.hms_touch_updated_at();

comment on table public.message_participants is
  'CONTACTS_V1 F1. DERIVADO y reconstruible desde communication_messages. Identidad = address_norm (nunca display_name).';
comment on table public.contact_addresses is
  'CONTACTS_V1 F1. DERIVADO. Unicidad (workspace_id, address_norm). Estadísticas solo por el constructor F3.';
comment on table public.own_address_aliases is
  'CONTACTS_V1 F1. Alias propios no conectados. detected = sugerencia; confirmed/rejected = decisión del usuario.';

alter table public.message_participants enable row level security;
alter table public.contact_addresses enable row level security;
alter table public.own_address_aliases enable row level security;

do $$ begin
  if exists (select 1 from pg_roles where rolname = 'anon') then
    revoke all on public.message_participants, public.contact_addresses, public.own_address_aliases
      from anon, authenticated;
  end if;
  if exists (select 1 from pg_roles where rolname = 'service_role') then
    grant select, insert, update, delete
      on public.message_participants, public.contact_addresses, public.own_address_aliases
      to service_role;
    grant usage on sequence public.message_participants_id_seq to service_role;
  end if;
end $$;
