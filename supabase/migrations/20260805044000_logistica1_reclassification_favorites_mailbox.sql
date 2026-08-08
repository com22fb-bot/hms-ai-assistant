alter table public.case_reclassification_runs
  add column if not exists total_messages integer not null default 0,
  add column if not exists processed_messages integer not null default 0,
  add column if not exists removed_cases integer not null default 0,
  add column if not exists without_case integer not null default 0,
  add column if not exists current_batch integer not null default 0,
  add column if not exists heartbeat_at timestamptz,
  add column if not exists initiated_by uuid references public.profiles(id) on delete set null,
  add column if not exists classifier_version text,
  add column if not exists cancel_requested boolean not null default false;

create unique index if not exists uq_case_reclassification_active_account
  on public.case_reclassification_runs(account_id)
  where status = 'running';

create table if not exists public.reclassification_backup_rows (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.case_reclassification_runs(id) on delete cascade,
  table_name text not null,
  source_id text,
  row_data jsonb not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_reclassification_backup_run
  on public.reclassification_backup_rows(run_id, table_name);

create table if not exists public.message_watch_rules (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  account_id uuid not null references public.communication_accounts(id) on delete cascade,
  profile_id uuid not null references public.profiles(id) on delete cascade,
  source_message_id uuid not null references public.communication_messages(id) on delete cascade,
  match_type text not null check (match_type in ('sender','subject','sender_subject')),
  sender_email text,
  normalized_subject text,
  display_label text,
  is_active boolean not null default true,
  notify_in_app boolean not null default true,
  notify_push boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(profile_id, source_message_id)
);

create index if not exists idx_message_watch_rules_active
  on public.message_watch_rules(account_id, profile_id, is_active);
create index if not exists idx_message_watch_rules_sender
  on public.message_watch_rules(account_id, sender_email)
  where is_active = true;
create index if not exists idx_message_watch_rules_subject
  on public.message_watch_rules(account_id, normalized_subject)
  where is_active = true;

create table if not exists public.message_watch_matches (
  id uuid primary key default gen_random_uuid(),
  rule_id uuid not null references public.message_watch_rules(id) on delete cascade,
  message_id uuid not null references public.communication_messages(id) on delete cascade,
  matched_at timestamptz not null default now(),
  read_at timestamptz,
  notified_at timestamptz,
  unique(rule_id, message_id)
);

create index if not exists idx_message_watch_matches_unread
  on public.message_watch_matches(rule_id, read_at, matched_at desc);

alter table public.reclassification_backup_rows enable row level security;
alter table public.message_watch_rules enable row level security;
alter table public.message_watch_matches enable row level security;

revoke all on public.reclassification_backup_rows from anon, authenticated;
revoke all on public.message_watch_rules from anon, authenticated;
revoke all on public.message_watch_matches from anon, authenticated;
