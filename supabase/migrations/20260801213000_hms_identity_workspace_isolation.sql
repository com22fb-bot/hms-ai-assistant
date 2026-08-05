-- ============================================================================
-- HMS AI Assistant
-- Sprint 4.10 — Identidad HMS y aislamiento inicial por workspace
-- Date: 2026-08-01
--
-- This migration is additive and tailored to the current HMS database:
--   - Supabase Auth contains the trusted identities.
--   - The existing development mailbox remains in the legacy workspace.
--   - Only the HMS profile that owns the current active mailbox is attached
--     to the legacy workspace; every other profile receives an isolated space.
--   - Future Auth users receive an isolated personal workspace automatically.
--   - OAuth states and mailbox connections are bound to profile/workspace.
-- ============================================================================

begin;

create extension if not exists pgcrypto;
create extension if not exists citext;

-- --------------------------------------------------------------------------
-- PROFILE METADATA LINKED TO auth.users
-- --------------------------------------------------------------------------

create table if not exists public.profiles (
    id uuid primary key references auth.users(id) on delete cascade,
    email citext,
    full_name text,
    phone text,
    language text not null default 'es',
    locale text not null default 'es-MX',
    timezone text not null default 'America/Mexico_City',
    is_active boolean not null default true,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now()),
    deleted_at timestamptz
);

alter table public.profiles
    add column if not exists email citext,
    add column if not exists full_name text,
    add column if not exists phone text,
    add column if not exists language text not null default 'es',
    add column if not exists locale text not null default 'es-MX',
    add column if not exists timezone text not null default 'America/Mexico_City',
    add column if not exists is_active boolean not null default true,
    add column if not exists metadata jsonb not null default '{}'::jsonb,
    add column if not exists created_at timestamptz not null default timezone('utc', now()),
    add column if not exists updated_at timestamptz not null default timezone('utc', now()),
    add column if not exists deleted_at timestamptz;

insert into public.profiles (
    id,
    email,
    full_name,
    language,
    locale,
    timezone,
    is_active,
    metadata,
    created_at,
    updated_at
)
select
    u.id,
    lower(u.email)::citext,
    nullif(trim(coalesce(u.raw_user_meta_data ->> 'full_name', '')), ''),
    coalesce(nullif(trim(u.raw_user_meta_data ->> 'language'), ''), 'es'),
    coalesce(nullif(trim(u.raw_user_meta_data ->> 'locale'), ''), 'es-MX'),
    coalesce(
        nullif(trim(u.raw_user_meta_data ->> 'timezone'), ''),
        'America/Mexico_City'
    ),
    true,
    '{}'::jsonb,
    coalesce(u.created_at, timezone('utc', now())),
    timezone('utc', now())
from auth.users u
where u.email is not null
on conflict (id)
do update set
    email = excluded.email,
    full_name = coalesce(excluded.full_name, public.profiles.full_name),
    language = coalesce(nullif(public.profiles.language, ''), excluded.language),
    locale = coalesce(nullif(public.profiles.locale, ''), excluded.locale),
    timezone = coalesce(nullif(public.profiles.timezone, ''), excluded.timezone),
    is_active = true,
    deleted_at = null,
    updated_at = timezone('utc', now());

create unique index if not exists uq_hms_profiles_email_active
    on public.profiles (lower(email::text))
    where email is not null and deleted_at is null;

-- --------------------------------------------------------------------------
-- WORKSPACE OWNERSHIP AND MEMBERSHIP
-- --------------------------------------------------------------------------

alter table public.workspaces
    add column if not exists owner_profile_id uuid
        references public.profiles(id) on delete set null;

create table if not exists public.workspace_members (
    id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null
        references public.workspaces(id) on delete cascade,
    profile_id uuid not null
        references public.profiles(id) on delete cascade,
    role text not null default 'viewer',
    status text not null default 'active',
    joined_at timestamptz,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now()),
    deleted_at timestamptz,
    constraint uq_hms_workspace_members unique (workspace_id, profile_id),
    constraint chk_hms_workspace_member_role check (
        role in ('owner', 'admin', 'manager', 'operator', 'viewer', 'auditor')
    ),
    constraint chk_hms_workspace_member_status check (
        status in ('invited', 'active', 'suspended', 'removed')
    )
);

alter table public.workspace_members
    add column if not exists role text not null default 'viewer',
    add column if not exists status text not null default 'active',
    add column if not exists joined_at timestamptz,
    add column if not exists created_at timestamptz not null default timezone('utc', now()),
    add column if not exists updated_at timestamptz not null default timezone('utc', now()),
    add column if not exists deleted_at timestamptz;

create unique index if not exists uq_hms_workspace_members_pair
    on public.workspace_members(workspace_id, profile_id);

create index if not exists idx_hms_workspace_members_profile_active
    on public.workspace_members(profile_id, status)
    where deleted_at is null;

-- --------------------------------------------------------------------------
-- MAILBOX AND OAUTH OWNERSHIP
-- --------------------------------------------------------------------------

alter table public.communication_accounts
    add column if not exists connected_by_profile_id uuid
        references public.profiles(id) on delete set null;

alter table public.oauth_states
    add column if not exists profile_id uuid
        references public.profiles(id) on delete cascade,
    add column if not exists workspace_id uuid
        references public.workspaces(id) on delete cascade,
    add column if not exists return_to text;

create index if not exists idx_hms_oauth_states_workspace
    on public.oauth_states(workspace_id, provider, expires_at);

create index if not exists idx_hms_accounts_workspace_provider
    on public.communication_accounts(workspace_id, provider, status);

-- --------------------------------------------------------------------------
-- EXISTING DEVELOPMENT WORKSPACE BACKFILL
-- --------------------------------------------------------------------------

-- The owner is selected by matching the active mailbox email to an HMS Auth
-- profile whenever possible. Only that owner is attached to the legacy
-- workspace. Other existing profiles are provisioned into separate personal
-- workspaces below, so they cannot see the legacy mailbox, messages or cases.

do $$
declare
    legacy_workspace_id uuid;
    legacy_mailbox_email text;
    selected_owner_profile_id uuid;
begin
    select ca.workspace_id, ca.email
      into legacy_workspace_id, legacy_mailbox_email
      from public.communication_accounts ca
      join public.oauth_credentials oc on oc.account_id = ca.id
     where ca.provider = 'google'
       and ca.status = 'active'
     order by ca.updated_at desc nulls last, ca.created_at asc nulls last
     limit 1;

    if legacy_workspace_id is null then
        select w.id
          into legacy_workspace_id
          from public.workspaces w
         where w.status = 'active'
         order by w.created_at asc nulls last, w.id asc
         limit 1;
    end if;

    if legacy_workspace_id is null then
        return;
    end if;

    select p.id
      into selected_owner_profile_id
      from public.profiles p
     where p.is_active = true
       and p.deleted_at is null
       and legacy_mailbox_email is not null
       and lower(p.email::text) = lower(legacy_mailbox_email)
     order by p.created_at asc, p.id asc
     limit 1;

    if selected_owner_profile_id is null then
        select p.id
          into selected_owner_profile_id
          from public.profiles p
         where p.is_active = true
           and p.deleted_at is null
         order by p.created_at asc, p.id asc
         limit 1;
    end if;

    if selected_owner_profile_id is null then
        return;
    end if;

    update public.workspaces w
       set owner_profile_id = coalesce(
           w.owner_profile_id,
           selected_owner_profile_id
       )
     where w.id = legacy_workspace_id;

    insert into public.workspace_members (
        workspace_id,
        profile_id,
        role,
        status,
        joined_at,
        deleted_at,
        updated_at
    )
    values (
        legacy_workspace_id,
        selected_owner_profile_id,
        'owner',
        'active',
        timezone('utc', now()),
        null,
        timezone('utc', now())
    )
    on conflict (workspace_id, profile_id)
    do update set
        role = 'owner',
        status = 'active',
        joined_at = coalesce(
            public.workspace_members.joined_at,
            excluded.joined_at
        ),
        deleted_at = null,
        updated_at = timezone('utc', now());

    update public.communication_accounts ca
       set connected_by_profile_id = coalesce(
           ca.connected_by_profile_id,
           (
               select p.id
                 from public.profiles p
                where ca.email is not null
                  and lower(p.email::text) = lower(ca.email)
                order by p.created_at asc, p.id asc
                limit 1
           ),
           selected_owner_profile_id
       )
     where ca.workspace_id = legacy_workspace_id;
end;
$$;

-- --------------------------------------------------------------------------
-- PERSONAL WORKSPACE PROVISIONING FOR ISOLATED USERS
-- --------------------------------------------------------------------------

create or replace function public.hms_ensure_personal_workspace(
    target_profile_id uuid
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
    existing_workspace_id uuid;
    created_workspace_id uuid;
    profile_name text;
    personal_slug text;
begin
    select wm.workspace_id
      into existing_workspace_id
      from public.workspace_members wm
     where wm.profile_id = target_profile_id
       and wm.status = 'active'
       and wm.deleted_at is null
     order by wm.joined_at asc nulls last, wm.created_at asc
     limit 1;

    if existing_workspace_id is not null then
        return existing_workspace_id;
    end if;

    select coalesce(
               nullif(trim(p.full_name), ''),
               split_part(p.email::text, '@', 1),
               'Usuario HMS'
           )
      into profile_name
      from public.profiles p
     where p.id = target_profile_id;

    if profile_name is null then
        raise exception 'No existe el perfil HMS %', target_profile_id;
    end if;

    personal_slug := 'personal-' || replace(target_profile_id::text, '-', '');

    insert into public.workspaces (
        name,
        slug,
        status,
        owner_profile_id
    )
    values (
        profile_name || ' — Personal',
        personal_slug,
        'active',
        target_profile_id
    )
    on conflict (slug)
    do update set
        owner_profile_id = coalesce(
            public.workspaces.owner_profile_id,
            excluded.owner_profile_id
        )
    returning id into created_workspace_id;

    insert into public.workspace_members (
        workspace_id,
        profile_id,
        role,
        status,
        joined_at,
        deleted_at,
        updated_at
    )
    values (
        created_workspace_id,
        target_profile_id,
        'owner',
        'active',
        timezone('utc', now()),
        null,
        timezone('utc', now())
    )
    on conflict (workspace_id, profile_id)
    do update set
        role = 'owner',
        status = 'active',
        joined_at = coalesce(
            public.workspace_members.joined_at,
            excluded.joined_at
        ),
        deleted_at = null,
        updated_at = timezone('utc', now());

    return created_workspace_id;
end;
$$;

create or replace function public.hms_handle_auth_user()
returns trigger
language plpgsql
security definer
set search_path = public, auth
as $$
begin
    insert into public.profiles (
        id,
        email,
        full_name,
        language,
        locale,
        timezone,
        is_active,
        metadata,
        created_at,
        updated_at,
        deleted_at
    )
    values (
        new.id,
        lower(new.email)::citext,
        nullif(trim(coalesce(new.raw_user_meta_data ->> 'full_name', '')), ''),
        coalesce(nullif(trim(new.raw_user_meta_data ->> 'language'), ''), 'es'),
        coalesce(nullif(trim(new.raw_user_meta_data ->> 'locale'), ''), 'es-MX'),
        coalesce(
            nullif(trim(new.raw_user_meta_data ->> 'timezone'), ''),
            'America/Mexico_City'
        ),
        true,
        '{}'::jsonb,
        coalesce(new.created_at, timezone('utc', now())),
        timezone('utc', now()),
        null
    )
    on conflict (id)
    do update set
        email = excluded.email,
        full_name = coalesce(excluded.full_name, public.profiles.full_name),
        language = excluded.language,
        locale = excluded.locale,
        timezone = excluded.timezone,
        is_active = true,
        deleted_at = null,
        updated_at = timezone('utc', now());

    perform public.hms_ensure_personal_workspace(new.id);
    return new;
end;
$$;

drop trigger if exists trg_hms_auth_user_identity on auth.users;
create trigger trg_hms_auth_user_identity
after insert or update of email, raw_user_meta_data on auth.users
for each row execute function public.hms_handle_auth_user();

-- Ensure every profile not assigned to the legacy mailbox workspace receives a
-- personal workspace. In the current project, the Yahoo HMS test account is
-- intentionally isolated here and will start without a connected mailbox.
do $$
declare
    profile_row record;
begin
    for profile_row in
        select p.id
          from public.profiles p
         where p.is_active = true
           and p.deleted_at is null
           and not exists (
               select 1
                 from public.workspace_members wm
                where wm.profile_id = p.id
                  and wm.status = 'active'
                  and wm.deleted_at is null
           )
    loop
        perform public.hms_ensure_personal_workspace(profile_row.id);
    end loop;
end;
$$;

-- --------------------------------------------------------------------------
-- UPDATED_AT AND RLS
-- --------------------------------------------------------------------------

create or replace function public.hms_set_updated_at()
returns trigger
language plpgsql
set search_path = public
as $$
begin
    new.updated_at = timezone('utc', now());
    return new;
end;
$$;

drop trigger if exists trg_hms_profiles_updated_at on public.profiles;
create trigger trg_hms_profiles_updated_at
before update on public.profiles
for each row execute function public.hms_set_updated_at();

drop trigger if exists trg_hms_workspace_members_updated_at
on public.workspace_members;
create trigger trg_hms_workspace_members_updated_at
before update on public.workspace_members
for each row execute function public.hms_set_updated_at();

create or replace function public.hms_is_workspace_member(
    target_workspace_id uuid
)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
    select exists (
        select 1
          from public.workspace_members wm
         where wm.workspace_id = target_workspace_id
           and wm.profile_id = auth.uid()
           and wm.status = 'active'
           and wm.deleted_at is null
    );
$$;

alter table public.profiles enable row level security;
alter table public.workspaces enable row level security;
alter table public.workspace_members enable row level security;
alter table public.communication_accounts enable row level security;

drop policy if exists "Users manage own profile" on public.profiles;
drop policy if exists hms_profiles_select_self on public.profiles;
create policy hms_profiles_select_self
on public.profiles for select to authenticated
using (id = auth.uid() and deleted_at is null);

drop policy if exists hms_workspaces_select_member on public.workspaces;
create policy hms_workspaces_select_member
on public.workspaces for select to authenticated
using (public.hms_is_workspace_member(id));

drop policy if exists hms_workspace_members_select_own on public.workspace_members;
create policy hms_workspace_members_select_own
on public.workspace_members for select to authenticated
using (profile_id = auth.uid() and deleted_at is null);

drop policy if exists hms_accounts_select_member on public.communication_accounts;
create policy hms_accounts_select_member
on public.communication_accounts for select to authenticated
using (public.hms_is_workspace_member(workspace_id));

grant select on public.profiles to authenticated;
grant select on public.workspaces to authenticated;
grant select on public.workspace_members to authenticated;
grant select on public.communication_accounts to authenticated;

revoke all on public.oauth_credentials from anon, authenticated;
revoke all on public.oauth_states from anon, authenticated;

revoke all on function public.hms_ensure_personal_workspace(uuid)
from public, anon, authenticated;
revoke all on function public.hms_handle_auth_user()
from public, anon, authenticated;
revoke all on function public.hms_set_updated_at()
from public, anon, authenticated;
revoke all on function public.hms_is_workspace_member(uuid)
from public, anon;
grant execute on function public.hms_is_workspace_member(uuid)
to authenticated;

commit;
