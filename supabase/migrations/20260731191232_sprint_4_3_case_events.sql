-- EVIDENCIAS: MENSAJES VINCULADOS A CASOS
-- ------------------------------------------------------------

create table if not exists public.case_messages (
    id uuid primary key default gen_random_uuid(),

    case_id uuid not null
        references public.intelligent_cases(id)
        on delete cascade,

    message_id uuid not null
        references public.communication_messages(id)
        on delete cascade,

    relation_type text not null default 'evidence',
    is_primary boolean not null default false,
    sequence_number integer,
    linked_at timestamptz not null default now(),

    unique(case_id, message_id)
);

create index if not exists idx_case_messages_case
    on public.case_messages(case_id, linked_at);

create unique index if not exists idx_case_messages_message_unique
    on public.case_messages(message_id);

-- ------------------------------------------------------------
-- PARTICIPANTES
-- ------------------------------------------------------------

create table if not exists public.case_participants (
    id uuid primary key default gen_random_uuid(),

    case_id uuid not null
        references public.intelligent_cases(id)
        on delete cascade,

    email text not null,
    display_name text,
    participant_role text not null default 'participant',

    message_count integer not null default 1,
    first_seen_at timestamptz not null default now(),
    last_seen_at timestamptz not null default now(),

    metadata jsonb not null default '{}'::jsonb,

    unique(case_id, email)
);

create index if not exists idx_case_participants_email
    on public.case_participants(email);

-- ------------------------------------------------------------
-- EVENTOS DE NEGOCIO
-- ------------------------------------------------------------

create table if not exists public.case_events (
    id uuid primary key default gen_random_uuid(),

    workspace_id uuid not null
        references public.workspaces(id)
        on delete cascade,

    case_id uuid not null
        references public.intelligent_cases(id)
        on delete cascade,

    message_id uuid
        references public.communication_messages(id)
        on delete set null,

    event_type text not null,
    level integer not null default 1,

    title text not null,
    description text,

    actor_type text not null default 'system',
    actor_identifier text,

    dedupe_key text,
    metadata jsonb not null default '{}'::jsonb,

    created_at timestamptz not null default now(),

    constraint case_events_level_check
        check (level between 0 and 4)
);

create index if not exists idx_case_events_case
    on public.case_events(case_id, created_at desc);

create index if not exists idx_case_events_workspace_level
    on public.case_events(workspace_id, level, created_at desc);

create unique index if not exists idx_case_events_dedupe
    on public.case_events(case_id, dedupe_key)
    where dedupe_key is not null;

-- ------------------------------------------------------------
