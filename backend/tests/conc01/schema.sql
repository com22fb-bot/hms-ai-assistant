-- Esquema sintético mínimo (subconjunto de producción) con las MISMAS
-- restricciones UNIQUE que la BD viva (leídas con pg_indexes el 30-oct-2026).
create extension if not exists pgcrypto;
drop table if exists case_notifications, case_events, case_participants, case_messages,
  intelligent_cases, organizational_patterns, communication_messages, communication_accounts,
  push_delivery_log cascade;
create table communication_accounts (id uuid primary key, workspace_id uuid, email text, provider text default 'yahoo');
create table communication_messages (
  id uuid primary key default gen_random_uuid(), account_id uuid references communication_accounts(id),
  thread_id text, external_message_id text, internet_message_id text, sender text, recipients jsonb default '[]',
  cc jsonb default '[]', bcc jsonb default '[]', subject text, body_text text, snippet text,
  received_at timestamptz, labels jsonb default '[]', is_unread boolean default true, direction text,
  case_processed boolean default false, processed_at timestamptz, in_reply_to text, references_header text,
  normalized_subject text, correlation_key text, triage_category text default 'unreviewed',
  actionability_score int, triage_reason text, triaged_at timestamptz, ai_processed boolean default false,
  push_notified_at timestamptz,
  unique (account_id, external_message_id));
create table intelligent_cases (
  id uuid primary key default gen_random_uuid(), workspace_id uuid, account_id uuid, primary_thread_id text,
  title text, normalized_subject text, case_type text, status text, priority text, risk_score int,
  confidence numeric, summary text, requested_action text, requester_name text, requester_email text,
  waiting_on text, opened_at timestamptz, last_activity_at timestamptz, source_count int, reminder_count int,
  metadata jsonb default '{}', updated_at timestamptz default now());
create table case_messages (id uuid primary key default gen_random_uuid(), case_id uuid references intelligent_cases(id),
  message_id uuid references communication_messages(id), relation_type text, is_primary boolean, linked_at timestamptz,
  unique (case_id, message_id));
create unique index idx_case_messages_message_unique on case_messages(message_id);
create table case_participants (id uuid primary key default gen_random_uuid(), case_id uuid, email text, display_name text,
  participant_role text, message_count int, first_seen_at timestamptz, last_seen_at timestamptz, unique (case_id, email));
create table case_events (id uuid primary key default gen_random_uuid(), workspace_id uuid, case_id uuid, message_id uuid,
  event_type text, level int, title text, description text, actor_type text, actor_identifier text, dedupe_key text,
  metadata jsonb, created_at timestamptz default now());
create unique index idx_case_events_dedupe on case_events(case_id, dedupe_key) where dedupe_key is not null;
create table case_notifications (id uuid primary key default gen_random_uuid(), workspace_id uuid, case_id uuid, event_id uuid,
  level int, channel text, title text, body text, metadata jsonb);
create table organizational_patterns (id uuid primary key default gen_random_uuid(), workspace_id uuid, pattern_type text,
  pattern_key text, pattern_value jsonb, occurrences int default 1, confidence numeric, first_seen_at timestamptz, last_seen_at timestamptz,
  metadata jsonb, created_at timestamptz default now(), updated_at timestamptz default now());
create table push_delivery_log (id uuid primary key default gen_random_uuid(), created_at timestamptz default now());
