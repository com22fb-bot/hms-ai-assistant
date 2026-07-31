-- NOTIFICACIONES DE EVENTOS
-- ------------------------------------------------------------

create table if not exists public.case_notifications (
    id uuid primary key default gen_random_uuid(),

    workspace_id uuid not null
        references public.workspaces(id)
        on delete cascade,

    case_id uuid not null
        references public.intelligent_cases(id)
        on delete cascade,

    event_id uuid
        references public.case_events(id)
        on delete set null,

    level integer not null default 2,
    channel text not null default 'dashboard',

    title text not null,
    body text,

    delivered_at timestamptz,
    read_at timestamptz,

    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),

    constraint case_notifications_level_check
        check (level between 0 and 4)
);

create index if not exists idx_case_notifications_unread
    on public.case_notifications(workspace_id, read_at, created_at desc);

-- ------------------------------------------------------------
