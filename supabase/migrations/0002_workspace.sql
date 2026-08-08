-- ============================================================================
-- HMS AI Assistant
-- Workspace Domain
-- Version: 1.0
-- Migration: 0002
-- Depends on: 0001_foundation_identity.sql
-- ============================================================================

begin;

-- ============================================================================
-- ENUM TYPES
-- ============================================================================

do $$
begin
    create type public.workspace_type as enum (
        'personal',
        'business',
        'enterprise'
    );
exception
    when duplicate_object then null;
end
$$;

do $$
begin
    create type public.workspace_status as enum (
        'active',
        'suspended',
        'archived'
    );
exception
    when duplicate_object then null;
end
$$;

do $$
begin
    create type public.workspace_member_role as enum (
        'owner',
        'admin',
        'manager',
        'operator',
        'viewer',
        'auditor'
    );
exception
    when duplicate_object then null;
end
$$;

do $$
begin
    create type public.workspace_member_status as enum (
        'invited',
        'active',
        'suspended',
        'removed'
    );
exception
    when duplicate_object then null;
end
$$;

-- ============================================================================
-- TABLES
-- ============================================================================

create table if not exists public.workspaces (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    slug citext not null unique,
    type public.workspace_type not null default 'business',
    status public.workspace_status not null default 'active',
    owner_profile_id uuid not null,
    default_locale text not null default 'es-MX',
    default_timezone text not null default 'America/Mexico_City',
    settings jsonb not null default '{}'::jsonb,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now()),
    deleted_at timestamptz,

    constraint fk_workspaces_owner_profile
        foreign key (owner_profile_id)
        references public.profiles(id)
        on delete restrict,

    constraint chk_workspaces_name_not_blank
        check (length(trim(name)) > 0),

    constraint chk_workspaces_slug
        check (
            slug::text ~ '^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$'
        ),

    constraint chk_workspaces_settings_object
        check (jsonb_typeof(settings) = 'object'),

    constraint chk_workspaces_metadata_object
        check (jsonb_typeof(metadata) = 'object')
);

comment on table public.workspaces is
'Top-level tenant boundary for organizations and personal accounts.';

comment on column public.workspaces.slug is
'Unique lowercase URL-safe workspace identifier.';

comment on column public.workspaces.settings is
'Workspace-level application configuration.';

create table if not exists public.workspace_members (
    id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null,
    profile_id uuid not null,
    role public.workspace_member_role not null default 'viewer',
    status public.workspace_member_status not null default 'invited',
    invited_by_profile_id uuid,
    invited_at timestamptz,
    joined_at timestamptz,
    last_active_at timestamptz,
    permissions jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now()),
    deleted_at timestamptz,

    constraint fk_workspace_members_workspace
        foreign key (workspace_id)
        references public.workspaces(id)
        on delete cascade,

    constraint fk_workspace_members_profile
        foreign key (profile_id)
        references public.profiles(id)
        on delete cascade,

    constraint fk_workspace_members_invited_by
        foreign key (invited_by_profile_id)
        references public.profiles(id)
        on delete set null,

    constraint uq_workspace_members_workspace_profile
        unique (workspace_id, profile_id),

    constraint chk_workspace_members_permissions_object
        check (jsonb_typeof(permissions) = 'object'),

    constraint chk_workspace_members_joined_status
        check (
            status <> 'active'
            or joined_at is not null
        )
);

comment on table public.workspace_members is
'Membership, role and workspace-specific permissions for a profile.';

comment on column public.workspace_members.permissions is
'Optional granular permission overrides stored as a JSON object.';

-- ============================================================================
-- INDEXES
-- ============================================================================

create index if not exists idx_workspaces_owner
    on public.workspaces (owner_profile_id)
    where deleted_at is null;

create index if not exists idx_workspaces_status
    on public.workspaces (status)
    where deleted_at is null;

create index if not exists idx_workspace_members_profile
    on public.workspace_members (profile_id, status)
    where deleted_at is null;

create index if not exists idx_workspace_members_workspace
    on public.workspace_members (workspace_id, role, status)
    where deleted_at is null;

create index if not exists idx_workspace_members_active
    on public.workspace_members (workspace_id, profile_id)
    where status = 'active' and deleted_at is null;

-- ============================================================================
-- UPDATED_AT TRIGGERS
-- ============================================================================

drop trigger if exists trg_workspaces_set_updated_at
on public.workspaces;

create trigger trg_workspaces_set_updated_at
before update on public.workspaces
for each row
execute function public.set_updated_at();

drop trigger if exists trg_workspace_members_set_updated_at
on public.workspace_members;

create trigger trg_workspace_members_set_updated_at
before update on public.workspace_members
for each row
execute function public.set_updated_at();

-- ============================================================================
-- SECURITY HELPER FUNCTIONS
-- ============================================================================

create or replace function public.is_workspace_owner(
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
        from public.workspaces w
        where w.id = target_workspace_id
          and w.owner_profile_id = auth.uid()
          and w.deleted_at is null
    );
$$;

comment on function public.is_workspace_owner(uuid) is
'Returns true when the authenticated profile owns the workspace.';

create or replace function public.is_workspace_member(
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
    )
    or public.is_workspace_owner(target_workspace_id);
$$;

comment on function public.is_workspace_member(uuid) is
'Returns true when the authenticated profile is an active member or owner.';

create or replace function public.has_workspace_role(
    target_workspace_id uuid,
    allowed_roles public.workspace_member_role[]
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
          and wm.role = any(allowed_roles)
          and wm.deleted_at is null
    )
    or (
        'owner' = any(allowed_roles)
        and public.is_workspace_owner(target_workspace_id)
    );
$$;

comment on function public.has_workspace_role(
    uuid,
    public.workspace_member_role[]
) is
'Checks whether the authenticated profile has one of the supplied workspace roles.';

-- ============================================================================
-- AUTOMATIC OWNER MEMBERSHIP
-- ============================================================================

create or replace function public.create_workspace_owner_membership()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
    insert into public.workspace_members (
        workspace_id,
        profile_id,
        role,
        status,
        joined_at
    )
    values (
        new.id,
        new.owner_profile_id,
        'owner',
        'active',
        timezone('utc', now())
    )
    on conflict (workspace_id, profile_id)
    do update
    set
        role = 'owner',
        status = 'active',
        joined_at = coalesce(
            public.workspace_members.joined_at,
            excluded.joined_at
        ),
        deleted_at = null,
        updated_at = timezone('utc', now());

    return new;
end;
$$;

comment on function public.create_workspace_owner_membership() is
'Creates or restores the active owner membership after workspace creation.';

drop trigger if exists trg_workspaces_create_owner_membership
on public.workspaces;

create trigger trg_workspaces_create_owner_membership
after insert on public.workspaces
for each row
execute function public.create_workspace_owner_membership();

-- Backfill owner memberships for any workspaces created before this trigger.

insert into public.workspace_members (
    workspace_id,
    profile_id,
    role,
    status,
    joined_at
)
select
    w.id,
    w.owner_profile_id,
    'owner',
    'active',
    coalesce(w.created_at, timezone('utc', now()))
from public.workspaces w
where w.deleted_at is null
on conflict (workspace_id, profile_id)
do update
set
    role = 'owner',
    status = 'active',
    joined_at = coalesce(
        public.workspace_members.joined_at,
        excluded.joined_at
    ),
    deleted_at = null,
    updated_at = timezone('utc', now());

-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================

alter table public.workspaces enable row level security;
alter table public.workspace_members enable row level security;

drop policy if exists workspaces_select_member
on public.workspaces;

create policy workspaces_select_member
on public.workspaces
for select
to authenticated
using (
    deleted_at is null
    and public.is_workspace_member(id)
);

drop policy if exists workspaces_insert_owner
on public.workspaces;

create policy workspaces_insert_owner
on public.workspaces
for insert
to authenticated
with check (
    owner_profile_id = auth.uid()
    and deleted_at is null
);

drop policy if exists workspaces_update_admin
on public.workspaces;

create policy workspaces_update_admin
on public.workspaces
for update
to authenticated
using (
    deleted_at is null
    and public.has_workspace_role(
        id,
        array[
            'owner',
            'admin'
        ]::public.workspace_member_role[]
    )
)
with check (
    public.has_workspace_role(
        id,
        array[
            'owner',
            'admin'
        ]::public.workspace_member_role[]
    )
);

drop policy if exists workspaces_delete_owner
on public.workspaces;

create policy workspaces_delete_owner
on public.workspaces
for delete
to authenticated
using (
    public.is_workspace_owner(id)
);

drop policy if exists workspace_members_select_member
on public.workspace_members;

create policy workspace_members_select_member
on public.workspace_members
for select
to authenticated
using (
    deleted_at is null
    and public.is_workspace_member(workspace_id)
);

drop policy if exists workspace_members_insert_admin
on public.workspace_members;

create policy workspace_members_insert_admin
on public.workspace_members
for insert
to authenticated
with check (
    public.has_workspace_role(
        workspace_id,
        array[
            'owner',
            'admin'
        ]::public.workspace_member_role[]
    )
);

drop policy if exists workspace_members_update_admin
on public.workspace_members;

create policy workspace_members_update_admin
on public.workspace_members
for update
to authenticated
using (
    deleted_at is null
    and public.has_workspace_role(
        workspace_id,
        array[
            'owner',
            'admin'
        ]::public.workspace_member_role[]
    )
)
with check (
    public.has_workspace_role(
        workspace_id,
        array[
            'owner',
            'admin'
        ]::public.workspace_member_role[]
    )
);

drop policy if exists workspace_members_delete_admin
on public.workspace_members;

create policy workspace_members_delete_admin
on public.workspace_members
for delete
to authenticated
using (
    public.has_workspace_role(
        workspace_id,
        array[
            'owner',
            'admin'
        ]::public.workspace_member_role[]
    )
    and profile_id <> auth.uid()
);

-- ============================================================================
-- GRANTS
-- ============================================================================

grant select, insert, update, delete
on public.workspaces
to authenticated;

grant select, insert, update, delete
on public.workspace_members
to authenticated;

revoke all
on function public.is_workspace_owner(uuid)
from public;

revoke all
on function public.is_workspace_member(uuid)
from public;

revoke all
on function public.has_workspace_role(
    uuid,
    public.workspace_member_role[]
)
from public;

grant execute
on function public.is_workspace_owner(uuid)
to authenticated;

grant execute
on function public.is_workspace_member(uuid)
to authenticated;

grant execute
on function public.has_workspace_role(
    uuid,
    public.workspace_member_role[]
)
to authenticated;

commit;