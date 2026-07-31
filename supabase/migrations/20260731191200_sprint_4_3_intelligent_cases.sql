-- CASOS INTELIGENTES
-- ------------------------------------------------------------

create table if not exists public.intelligent_cases (
    id uuid primary key default gen_random_uuid(),

    workspace_id uuid not null
        references public.workspaces(id)
        on delete cascade,

    account_id uuid
        references public.communication_accounts(id)
        on delete cascade,

    primary_thread_id uuid
        references public.communication_threads(id)
        on delete set null,

    title text not null,
    normalized_subject text,
    case_type text not null default 'general',

    status text not null default 'new',
    priority text not null default 'normal',
    risk_score integer not null default 20,
    confidence numeric(5,4) not null default 0.6000,

    summary text,
    requested_action text,

    requester_name text,
    requester_email text,
    current_owner_email text,

    waiting_on text not null default 'internal',

    opened_at timestamptz not null default now(),
    last_activity_at timestamptz not null default now(),
    due_at timestamptz,
    resolved_at timestamptz,
    closed_at timestamptz,

    source_count integer not null default 0,
    reminder_count integer not null default 0,

    metadata jsonb not null default '{}'::jsonb,

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),

    constraint intelligent_cases_status_check
        check (
            status in (
                'new',
                'analyzing',
                'in_progress',
                'delegated',
                'waiting_internal',
                'waiting_external',
                'resolved',
                'closed',
                'archived'
            )
        ),

    constraint intelligent_cases_priority_check
        check (
            priority in (
                'low',
                'normal',
                'high',
                'critical'
            )
        ),

    constraint intelligent_cases_waiting_on_check
        check (
            waiting_on in (
                'internal',
                'external',
                'none'
            )
        ),

    constraint intelligent_cases_risk_score_check
        check (risk_score between 0 and 100),

    constraint intelligent_cases_source_count_check
        check (source_count >= 0),

    constraint intelligent_cases_reminder_count_check
        check (reminder_count >= 0)
);

create index if not exists idx_cases_workspace_status
    on public.intelligent_cases(workspace_id, status, last_activity_at desc);

create index if not exists idx_cases_account_priority
    on public.intelligent_cases(account_id, priority, last_activity_at desc);

create index if not exists idx_cases_thread
    on public.intelligent_cases(account_id, primary_thread_id);

create index if not exists idx_cases_normalized_subject
    on public.intelligent_cases(account_id, normalized_subject);

create index if not exists idx_cases_due
    on public.intelligent_cases(due_at)
    where due_at is not null;

-- ------------------------------------------------------------
