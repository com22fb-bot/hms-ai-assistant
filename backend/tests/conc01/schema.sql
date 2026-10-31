-- Esquema local desechable que REPLICA la estructura de producción de las tablas que usa
-- la RPC (leída SOLO con consultas de catálogo el 31-oct-2026; Postgres 17.6 en Supabase):
-- columnas y tipos, NOT NULL, defaults, CHECK, PK, FK, UNIQUE, índices y triggers updated_at.
-- Se omiten solo columnas/tablas que la RPC no toca. Datos 100% sintéticos.
create extension if not exists pgcrypto;
drop table if exists case_notifications, case_events, case_participants, case_messages,
  intelligent_cases, organizational_patterns, communication_messages, communication_threads,
  communication_accounts, workspaces, push_delivery_log cascade;

create or replace function public.set_updated_at() returns trigger language plpgsql
set search_path to 'public' as $$ begin NEW.updated_at = now(); return NEW; end; $$;

create table workspaces (id uuid primary key default gen_random_uuid());
create table communication_accounts (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null references workspaces(id),
  email text, provider text not null default 'yahoo', status text default 'active');
create table communication_threads (id uuid primary key default gen_random_uuid());
create table communication_messages (
  id uuid primary key default gen_random_uuid(),
  thread_id uuid references communication_threads(id) on delete cascade,
  account_id uuid references communication_accounts(id) on delete cascade,
  provider text, external_message_id text, internet_message_id text, sender text, recipients jsonb,
  cc jsonb, bcc jsonb, subject text, body_text text, body_html text, snippet text,
  received_at timestamptz, labels jsonb not null default '[]', is_unread boolean not null default true,
  direction text not null default 'inbound', case_processed boolean not null default false,
  processed_at timestamptz, in_reply_to text, references_header jsonb not null default '[]',
  normalized_subject text, correlation_key text,
  triage_category text not null default 'unreviewed', actionability_score integer, triage_reason text,
  triaged_at timestamptz, ai_processed boolean default false, has_attachments boolean default false,
  push_notified_at timestamptz, brain_confidence numeric, brain_signals jsonb,
  created_at timestamptz default now(), updated_at timestamptz not null default now(),
  unique (account_id, external_message_id),
  constraint communication_messages_direction_check check ((direction = any (array['inbound'::text, 'outbound'::text, 'draft'::text, 'system'::text]))),
  constraint communication_messages_triage_category_check check ((triage_category = any (array['unreviewed'::text, 'action_required'::text, 'waiting_external'::text, 'review'::text, 'notice'::text, 'informational'::text, 'automated'::text, 'promotional'::text, 'social'::text]))));
create index idx_messages_case_processing on communication_messages (account_id, case_processed, received_at);
create index idx_messages_thread_received on communication_messages (thread_id, received_at desc);
create table intelligent_cases (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null references workspaces(id) on delete cascade,
  account_id uuid references communication_accounts(id) on delete cascade,
  primary_thread_id uuid references communication_threads(id) on delete set null,
  title text not null, normalized_subject text, case_type text not null default 'general',
  status text not null default 'new', priority text not null default 'normal', risk_score integer not null default 0,
  confidence numeric not null default 0.5, summary text, requested_action text, requester_name text,
  requester_email text, current_owner_email text, waiting_on text not null default 'none',
  opened_at timestamptz not null default now(), last_activity_at timestamptz not null default now(),
  due_at timestamptz, event_at timestamptz, resolved_at timestamptz, closed_at timestamptz,
  source_count integer not null default 1, reminder_count integer not null default 0,
  triage_category text not null default 'unreviewed', triage_reason text, triaged_at timestamptz,
  actionability_score integer, metadata jsonb not null default '{}',
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  constraint intelligent_cases_priority_check check ((priority = any (array['low'::text, 'normal'::text, 'high'::text, 'critical'::text]))),
  constraint intelligent_cases_reminder_count_check check ((reminder_count >= 0)),
  constraint intelligent_cases_risk_score_check check (((risk_score >= 0) and (risk_score <= 100))),
  constraint intelligent_cases_source_count_check check ((source_count >= 0)),
  constraint intelligent_cases_status_check check ((status = any (array['new'::text, 'analyzing'::text, 'in_progress'::text, 'delegated'::text, 'waiting_internal'::text, 'waiting_external'::text, 'resolved'::text, 'closed'::text, 'archived'::text, 'scheduled'::text, 'no_action'::text, 'needs_review'::text]))),
  constraint intelligent_cases_triage_category_check check ((triage_category = any (array['unreviewed'::text, 'action_required'::text, 'waiting_external'::text, 'review'::text, 'informational'::text, 'automated'::text, 'promotional'::text]))),
  constraint intelligent_cases_waiting_on_check check ((waiting_on = any (array['internal'::text, 'external'::text, 'none'::text]))));
create trigger trg_intelligent_cases_updated before update on intelligent_cases for each row execute function set_updated_at();
create table case_messages (
  id uuid primary key default gen_random_uuid(), case_id uuid not null references intelligent_cases(id) on delete cascade,
  message_id uuid not null references communication_messages(id) on delete cascade,
  relation_type text not null default 'evidence', is_primary boolean not null default false,
  sequence_number integer, linked_at timestamptz not null default now(), unique (case_id, message_id));
create unique index idx_case_messages_message_unique on case_messages(message_id);
create index idx_case_messages_case on case_messages (case_id, linked_at);
create table case_participants (
  id uuid primary key default gen_random_uuid(), case_id uuid not null references intelligent_cases(id) on delete cascade,
  email text not null, display_name text, participant_role text not null default 'participant',
  message_count integer not null default 1, first_seen_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(), metadata jsonb not null default '{}', unique (case_id, email));
create table case_events (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null references workspaces(id) on delete cascade,
  case_id uuid not null references intelligent_cases(id) on delete cascade,
  message_id uuid references communication_messages(id) on delete set null,
  event_type text not null, level integer not null default 1, title text not null, description text,
  actor_type text not null default 'system', actor_identifier text, dedupe_key text,
  metadata jsonb not null default '{}', created_at timestamptz not null default now(),
  constraint case_events_level_check check (((level >= 0) and (level <= 4))));
create unique index idx_case_events_dedupe on case_events(case_id, dedupe_key) where dedupe_key is not null;
create index idx_case_events_message on case_events (message_id);
create table case_notifications (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null references workspaces(id) on delete cascade,
  case_id uuid not null references intelligent_cases(id) on delete cascade,
  event_id uuid references case_events(id) on delete set null, level integer not null default 1,
  channel text not null default 'dashboard', title text not null, body text, delivered_at timestamptz,
  read_at timestamptz, metadata jsonb not null default '{}', created_at timestamptz not null default now(),
  constraint case_notifications_level_check check (((level >= 0) and (level <= 4))));
create table organizational_patterns (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null references workspaces(id) on delete cascade,
  pattern_type text not null, pattern_key text not null, pattern_value jsonb not null default '{}',
  occurrences integer not null default 1, confidence numeric not null default 0.5,
  first_seen_at timestamptz not null default now(), last_seen_at timestamptz not null default now(),
  updated_at timestamptz not null default now(), unique (workspace_id, pattern_type, pattern_key));
create trigger trg_organizational_patterns_updated before update on organizational_patterns for each row execute function set_updated_at();
-- RLS habilitada (no forzada) como en producción; el rol de pruebas, como service_role, la salta.
alter table communication_messages enable row level security;
alter table communication_accounts enable row level security;
alter table intelligent_cases enable row level security;
alter table case_messages enable row level security;
alter table case_participants enable row level security;
alter table case_events enable row level security;
alter table case_notifications enable row level security;
alter table organizational_patterns enable row level security;
create table push_delivery_log (id uuid primary key default gen_random_uuid(), created_at timestamptz default now());
