-- APRENDIZAJE ORGANIZACIONAL INICIAL
-- ------------------------------------------------------------

create table if not exists public.organizational_patterns (
    id uuid primary key default gen_random_uuid(),

    workspace_id uuid not null
        references public.workspaces(id)
        on delete cascade,

    pattern_type text not null,
    pattern_key text not null,
    pattern_value jsonb not null default '{}'::jsonb,

    occurrences integer not null default 1,
    confidence numeric(5,4) not null default 0.5000,

    first_seen_at timestamptz not null default now(),
    last_seen_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),

    unique(workspace_id, pattern_type, pattern_key)
);

create index if not exists idx_organizational_patterns_lookup
    on public.organizational_patterns(
        workspace_id,
        pattern_type,
        occurrences desc
    );

-- ------------------------------------------------------------
-- TRIGGERS
-- ------------------------------------------------------------

drop trigger if exists trg_intelligent_cases_updated
    on public.intelligent_cases;

create trigger trg_intelligent_cases_updated
before update on public.intelligent_cases
for each row
execute function set_updated_at();

drop trigger if exists trg_organizational_patterns_updated
    on public.organizational_patterns;

create trigger trg_organizational_patterns_updated
before update on public.organizational_patterns
for each row
execute function set_updated_at();

-- ------------------------------------------------------------
