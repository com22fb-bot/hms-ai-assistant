-- ============================================================================
-- HMS AI Assistant
-- Initial Database Schema
-- Version: 1.0 (Foundation: Extensions, Types, Identity)
-- Migration: 0001
-- ============================================================================
--
-- Architecture:
--   docs/architecture/PLATFORM_ARCHITECTURE_V1.md
--
-- Schema specification:
--   docs/database/SCHEMA_V1.md
--
-- Notes:
--   - Designed for Supabase/PostgreSQL.
--   - This migration creates the foundation and Identity domain.
--   - Workspace, Mail, Messaging, AI, Productivity, Security and Event
--     domains will be added in subsequent migrations.
--
-- ============================================================================

begin;

-- ============================================================================
-- EXTENSIONS
-- ============================================================================

create extension if not exists pgcrypto;
create extension if not exists citext;

-- ============================================================================
-- ENUM TYPES
-- ============================================================================

do $$
begin
    if not exists (
        select 1
        from pg_type t
        join pg_namespace n on n.oid = t.typnamespace
        where t.typname = 'device_platform'
          and n.nspname = 'public'
    ) then
        create type public.device_platform as enum (
            'web',
            'android',
            'ios',
            'windows',
            'macos',
            'linux'
        );
    end if;
end
$$;

do $$
begin
    if not exists (
        select 1
        from pg_type t
        join pg_namespace n on n.oid = t.typnamespace
        where t.typname = 'device_trust_level'
          and n.nspname = 'public'
    ) then
        create type public.device_trust_level as enum (
            'unknown',
            'trusted',
            'restricted',
            'blocked'
        );
    end if;
end
$$;

do $$
begin
    if not exists (
        select 1
        from pg_type t
        join pg_namespace n on n.oid = t.typnamespace
        where t.typname = 'device_risk_level'
          and n.nspname = 'public'
    ) then
        create type public.device_risk_level as enum (
            'low',
            'medium',
            'high',
            'critical'
        );
    end if;
end
$$;

-- ============================================================================
-- UTILITY FUNCTIONS
-- ============================================================================

create or replace function public.set_updated_at()
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

comment on function public.set_updated_at()
is 'Updates the updated_at column before a row is modified.';

-- ============================================================================
-- IDENTITY DOMAIN
-- ============================================================================

create table if not exists public.profiles (
    id uuid primary key,
    email citext not null,
    full_name text,
    avatar_url text,
    phone text,
    locale text not null default 'es-MX',
    timezone text not null default 'America/Mexico_City',
    is_active boolean not null default true,
    last_seen_at timestamptz,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now()),
    deleted_at timestamptz,

    constraint fk_profiles_auth_user
        foreign key (id)
        references auth.users(id)
        on update cascade
        on delete cascade,

    constraint uq_profiles_email
        unique (email),

    constraint chk_profiles_email_not_blank
        check (length(trim(email::text)) > 0),

    constraint chk_profiles_full_name_not_blank
        check (full_name is null or length(trim(full_name)) > 0),

    constraint chk_profiles_locale_not_blank
        check (length(trim(locale)) > 0),

    constraint chk_profiles_timezone_not_blank
        check (length(trim(timezone)) > 0),

    constraint chk_profiles_metadata_object
        check (jsonb_typeof(metadata) = 'object'),

    constraint chk_profiles_deleted_state
        check (
            deleted_at is null
            or is_active = false
        )
);

comment on table public.profiles
is 'Application profile associated one-to-one with a Supabase Auth user.';

comment on column public.profiles.id
is 'Primary key and foreign key to auth.users.id.';

comment on column public.profiles.email
is 'Normalized user email address. Stored as citext for case-insensitive comparison.';

comment on column public.profiles.metadata
is 'Flexible non-sensitive user metadata. Secrets must never be stored here.';

comment on column public.profiles.deleted_at
is 'Soft-deletion timestamp.';

create table if not exists public.registered_devices (
    id uuid primary key default gen_random_uuid(),
    profile_id uuid not null,
    device_name text,
    platform public.device_platform not null,
    device_identifier_hash text not null,
    public_key text,
    trust_level public.device_trust_level not null default 'unknown',
    risk_level public.device_risk_level not null default 'low',
    app_version text,
    operating_system text,
    browser text,
    user_agent text,
    ip_address inet,
    last_authenticated_at timestamptz,
    last_seen_at timestamptz,
    revoked_at timestamptz,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now()),
    deleted_at timestamptz,

    constraint fk_registered_devices_profile
        foreign key (profile_id)
        references public.profiles(id)
        on update cascade
        on delete cascade,

    constraint uq_registered_devices_profile_identifier
        unique (profile_id, device_identifier_hash),

    constraint chk_registered_devices_name_not_blank
        check (device_name is null or length(trim(device_name)) > 0),

    constraint chk_registered_devices_identifier_not_blank
        check (length(trim(device_identifier_hash)) > 0),

    constraint chk_registered_devices_public_key_not_blank
        check (public_key is null or length(trim(public_key)) > 0),

    constraint chk_registered_devices_metadata_object
        check (jsonb_typeof(metadata) = 'object'),

    constraint chk_registered_devices_revocation_state
        check (
            revoked_at is null
            or trust_level = 'blocked'
        ),

    constraint chk_registered_devices_deleted_state
        check (
            deleted_at is null
            or revoked_at is not null
        )
);

comment on table public.registered_devices
is 'Cryptographically identified devices registered to a user profile.';

comment on column public.registered_devices.device_identifier_hash
is 'One-way hash of the application-specific device identifier. Never store MAC addresses.';

comment on column public.registered_devices.public_key
is 'Optional WebAuthn/passkey or application device public key.';

-- ============================================================================
-- INDEXES
-- ============================================================================

create index if not exists idx_profiles_active
    on public.profiles (is_active)
    where deleted_at is null;

create index if not exists idx_profiles_last_seen_at
    on public.profiles (last_seen_at desc)
    where deleted_at is null;

create index if not exists idx_profiles_created_at
    on public.profiles (created_at desc);

create index if not exists idx_registered_devices_profile_id
    on public.registered_devices (profile_id)
    where deleted_at is null;

create index if not exists idx_registered_devices_trust_level
    on public.registered_devices (trust_level)
    where deleted_at is null;

create index if not exists idx_registered_devices_risk_level
    on public.registered_devices (risk_level)
    where deleted_at is null;

create index if not exists idx_registered_devices_last_seen_at
    on public.registered_devices (last_seen_at desc)
    where deleted_at is null;

create index if not exists idx_registered_devices_active_profile
    on public.registered_devices (
        profile_id,
        trust_level,
        risk_level
    )
    where deleted_at is null
      and revoked_at is null;

-- ============================================================================
-- TRIGGERS
-- ============================================================================

drop trigger if exists trg_profiles_set_updated_at
on public.profiles;

create trigger trg_profiles_set_updated_at
before update on public.profiles
for each row
execute function public.set_updated_at();

drop trigger if exists trg_registered_devices_set_updated_at
on public.registered_devices;

create trigger trg_registered_devices_set_updated_at
before update on public.registered_devices
for each row
execute function public.set_updated_at();

create or replace function public.handle_new_auth_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
    insert into public.profiles (
        id,
        email,
        full_name,
        avatar_url,
        locale,
        timezone,
        created_at,
        updated_at
    )
    values (
        new.id,
        new.email,
        nullif(trim(coalesce(new.raw_user_meta_data ->> 'full_name', '')), ''),
        nullif(trim(coalesce(new.raw_user_meta_data ->> 'avatar_url', '')), ''),
        coalesce(
            nullif(trim(coalesce(new.raw_user_meta_data ->> 'locale', '')), ''),
            'es-MX'
        ),
        coalesce(
            nullif(trim(coalesce(new.raw_user_meta_data ->> 'timezone', '')), ''),
            'America/Mexico_City'
        ),
        timezone('utc', now()),
        timezone('utc', now())
    )
    on conflict (id) do update
    set
        email = excluded.email,
        full_name = coalesce(public.profiles.full_name, excluded.full_name),
        avatar_url = coalesce(public.profiles.avatar_url, excluded.avatar_url),
        updated_at = timezone('utc', now());

    return new;
end;
$$;

comment on function public.handle_new_auth_user()
is 'Creates or updates the public profile associated with a Supabase Auth user.';

drop trigger if exists on_auth_user_created
on auth.users;

create trigger on_auth_user_created
after insert or update of email, raw_user_meta_data
on auth.users
for each row
execute function public.handle_new_auth_user();

insert into public.profiles (
    id,
    email,
    full_name,
    avatar_url,
    locale,
    timezone,
    created_at,
    updated_at
)
select
    u.id,
    u.email,
    nullif(trim(coalesce(u.raw_user_meta_data ->> 'full_name', '')), ''),
    nullif(trim(coalesce(u.raw_user_meta_data ->> 'avatar_url', '')), ''),
    coalesce(
        nullif(trim(coalesce(u.raw_user_meta_data ->> 'locale', '')), ''),
        'es-MX'
    ),
    coalesce(
        nullif(trim(coalesce(u.raw_user_meta_data ->> 'timezone', '')), ''),
        'America/Mexico_City'
    ),
    coalesce(u.created_at, timezone('utc', now())),
    timezone('utc', now())
from auth.users u
where u.email is not null
on conflict (id) do update
set
    email = excluded.email,
    full_name = coalesce(public.profiles.full_name, excluded.full_name),
    avatar_url = coalesce(public.profiles.avatar_url, excluded.avatar_url),
    updated_at = timezone('utc', now());

-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================

alter table public.profiles enable row level security;
alter table public.registered_devices enable row level security;

drop policy if exists profiles_select_own
on public.profiles;

create policy profiles_select_own
on public.profiles
for select
to authenticated
using (
    id = auth.uid()
    and deleted_at is null
);

drop policy if exists profiles_insert_own
on public.profiles;

create policy profiles_insert_own
on public.profiles
for insert
to authenticated
with check (
    id = auth.uid()
);

drop policy if exists profiles_update_own
on public.profiles;

create policy profiles_update_own
on public.profiles
for update
to authenticated
using (
    id = auth.uid()
    and deleted_at is null
)
with check (
    id = auth.uid()
);

drop policy if exists registered_devices_select_own
on public.registered_devices;

create policy registered_devices_select_own
on public.registered_devices
for select
to authenticated
using (
    profile_id = auth.uid()
    and deleted_at is null
);

drop policy if exists registered_devices_insert_own
on public.registered_devices;

create policy registered_devices_insert_own
on public.registered_devices
for insert
to authenticated
with check (
    profile_id = auth.uid()
);

drop policy if exists registered_devices_update_own
on public.registered_devices;

create policy registered_devices_update_own
on public.registered_devices
for update
to authenticated
using (
    profile_id = auth.uid()
    and deleted_at is null
)
with check (
    profile_id = auth.uid()
);

-- ============================================================================
-- GRANTS
-- ============================================================================

grant usage on schema public to authenticated;

grant select, insert, update
on public.profiles
to authenticated;

grant select, insert, update
on public.registered_devices
to authenticated;

commit;