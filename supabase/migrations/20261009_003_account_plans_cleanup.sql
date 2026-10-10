-- Planes de cuenta (prueba / mensual / anual) y registro de la limpieza diaria.
-- Solo el backend (service role) lee y escribe: RLS activo sin políticas.
create table if not exists public.account_plans (
    user_id uuid primary key references auth.users(id) on delete cascade,
    plan_code text not null default 'trial' check (plan_code in ('trial', 'monthly', 'annual')),
    status text not null default 'trialing' check (status in ('trialing', 'active', 'lapsed', 'canceled')),
    trial_ends_at timestamptz,
    period_ends_at timestamptz,
    reminder_mid_sent_at timestamptz,
    reminder_final_sent_at timestamptz,
    last_manual_reminder_at timestamptz,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);
alter table public.account_plans enable row level security;
revoke all on public.account_plans from anon, authenticated;

create table if not exists public.account_cleanup_runs (
    id uuid primary key default gen_random_uuid(),
    ran_at timestamptz not null default timezone('utc', now()),
    dry_run boolean not null,
    trial_due integer not null default 0,
    lapsed_due integer not null default 0,
    deleted integer not null default 0,
    skipped_protected integer not null default 0,
    reminders_mid integer not null default 0,
    reminders_final integer not null default 0,
    details jsonb not null default '{}'::jsonb
);
alter table public.account_cleanup_runs enable row level security;
revoke all on public.account_cleanup_runs from anon, authenticated;
