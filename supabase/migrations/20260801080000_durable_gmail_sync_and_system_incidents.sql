-- HMS AI Assistant 4.7
-- Durable Gmail synchronization and persistent incident log.
-- Applied to Supabase on 2026-08-01.

begin;

create table if not exists public.gmail_sync_jobs (
    id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null references public.workspaces(id) on delete cascade,
    account_id uuid not null references public.communication_accounts(id) on delete cascade,
    status text not null default 'queued',
    mode text not null default 'historical',
    query text,
    next_page_token text,
    batch_size integer not null default 50,
    process_cases boolean not null default true,
    pages_completed integer not null default 0,
    messages_found integer not null default 0,
    messages_inserted integer not null default 0,
    duplicates integer not null default 0,
    cases_processed integer not null default 0,
    created_cases integer not null default 0,
    linked_cases integer not null default 0,
    errors integer not null default 0,
    retry_count integer not null default 0,
    max_retries integer not null default 3,
    cancel_requested boolean not null default false,
    worker_id text,
    lease_expires_at timestamptz,
    last_error text,
    metadata jsonb not null default '{}'::jsonb,
    started_at timestamptz,
    heartbeat_at timestamptz,
    completed_at timestamptz,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now()),
    constraint chk_gmail_sync_jobs_status check (
        status in ('queued','running','paused','interrupted','completed','failed','cancelled')
    ),
    constraint chk_gmail_sync_jobs_mode check (
        mode in ('historical','incremental','custom')
    ),
    constraint chk_gmail_sync_jobs_batch_size check (batch_size between 1 and 100),
    constraint chk_gmail_sync_jobs_retry_controls check (
        retry_count >= 0 and max_retries between 0 and 10
    ),
    constraint chk_gmail_sync_jobs_metadata_object check (
        jsonb_typeof(metadata) = 'object'
    )
);

create unique index if not exists uq_gmail_sync_jobs_active_account
    on public.gmail_sync_jobs(account_id)
    where status in ('queued','running','paused','interrupted');

create index if not exists idx_gmail_sync_jobs_workspace_created
    on public.gmail_sync_jobs(workspace_id, created_at desc);
create index if not exists idx_gmail_sync_jobs_account_created
    on public.gmail_sync_jobs(account_id, created_at desc);
create index if not exists idx_gmail_sync_jobs_status_heartbeat
    on public.gmail_sync_jobs(status, heartbeat_at);

create table if not exists public.system_incidents (
    id uuid primary key default gen_random_uuid(),
    incident_code text not null unique,
    workspace_id uuid references public.workspaces(id) on delete set null,
    account_id uuid references public.communication_accounts(id) on delete set null,
    sync_job_id uuid references public.gmail_sync_jobs(id) on delete set null,
    occurred_at timestamptz not null default timezone('utc', now()),
    environment text not null default 'development',
    component text not null,
    severity text not null default 'medium',
    event_type text not null,
    summary text not null,
    technical_detail text,
    http_status integer,
    request_id text,
    detected_by text not null default 'system',
    status text not null default 'open',
    resolved_at timestamptz,
    resolution text,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now()),
    constraint chk_system_incidents_severity check (
        severity in ('info','low','medium','high','critical')
    ),
    constraint chk_system_incidents_status check (
        status in ('open','investigating','resolved','ignored')
    ),
    constraint chk_system_incidents_http_status check (
        http_status is null or http_status between 100 and 599
    ),
    constraint chk_system_incidents_resolution check (
        status <> 'resolved' or resolved_at is not null
    ),
    constraint chk_system_incidents_metadata_object check (
        jsonb_typeof(metadata) = 'object'
    )
);

create index if not exists idx_system_incidents_workspace_occurred
    on public.system_incidents(workspace_id, occurred_at desc);
create index if not exists idx_system_incidents_status_severity
    on public.system_incidents(status, severity, occurred_at desc);
create index if not exists idx_system_incidents_sync_job
    on public.system_incidents(sync_job_id)
    where sync_job_id is not null;

create or replace function public.hms_touch_updated_at()
returns trigger
language plpgsql
security invoker
set search_path = public
as $$
begin
    new.updated_at = timezone('utc', now());
    return new;
end;
$$;

drop trigger if exists trg_gmail_sync_jobs_updated_at on public.gmail_sync_jobs;
create trigger trg_gmail_sync_jobs_updated_at
before update on public.gmail_sync_jobs
for each row execute function public.hms_touch_updated_at();

drop trigger if exists trg_system_incidents_updated_at on public.system_incidents;
create trigger trg_system_incidents_updated_at
before update on public.system_incidents
for each row execute function public.hms_touch_updated_at();

alter table public.gmail_sync_jobs enable row level security;
alter table public.system_incidents enable row level security;

commit;
