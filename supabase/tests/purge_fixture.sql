-- Esquema mínimo que replica las FK reales de producción (23-oct-2026) para probar admin_purge_user v2.
do $$ begin
  if not exists (select 1 from pg_roles where rolname='anon') then create role anon; end if;
  if not exists (select 1 from pg_roles where rolname='authenticated') then create role authenticated; end if;
  if not exists (select 1 from pg_roles where rolname='service_role') then create role service_role; end if;
end $$;
create schema if not exists auth;
create table auth.users (id uuid primary key, email text);
create table auth.identities (id uuid primary key default gen_random_uuid(), user_id uuid references auth.users(id) on delete cascade);
create table public.profiles (id uuid primary key references auth.users(id) on delete cascade, email text, deleted_at timestamptz);
create table public.users (id uuid primary key, email text not null);
create table public.admin_allowlist (user_id uuid primary key, created_at timestamptz default now());
create table public.admin_events (id uuid primary key default gen_random_uuid(), source text, severity text, title text not null,
  detail text, status text, created_by text, meta jsonb, created_at timestamptz default now());
create table public.workspaces (id uuid primary key, name text not null, owner_profile_id uuid references public.profiles(id) on delete set null);
create table public.workspace_members (id uuid primary key default gen_random_uuid(), workspace_id uuid not null references public.workspaces(id),
  profile_id uuid not null references public.profiles(id) on delete cascade, role text, status text default 'active',
  joined_at timestamptz, created_at timestamptz default now(), deleted_at timestamptz);
create table public.communication_accounts (id uuid primary key, workspace_id uuid references public.workspaces(id), provider text,
  email text, status text, address_key text, connected_by_profile_id uuid references public.profiles(id) on delete set null,
  last_sync_at timestamptz, created_at timestamptz default now(), updated_at timestamptz);
create table public.oauth_credentials (id uuid primary key default gen_random_uuid(), account_id uuid references public.communication_accounts(id) on delete cascade, updated_at timestamptz default now());
create table public.communication_threads (id uuid primary key, account_id uuid references public.communication_accounts(id) on delete cascade);
create table public.communication_messages (id uuid primary key, thread_id uuid references public.communication_threads(id) on delete cascade,
  account_id uuid references public.communication_accounts(id) on delete cascade, created_at timestamptz default now(), processed_at timestamptz);
create table public.attachments (id uuid primary key default gen_random_uuid(), message_id uuid references public.communication_messages(id) on delete cascade, storage_path text);
create table public.gmail_sync_jobs (id uuid primary key default gen_random_uuid(), workspace_id uuid references public.workspaces(id), account_id uuid references public.communication_accounts(id) on delete cascade,
  mode text, status text, messages_inserted int, duplicates int, errors int, started_at timestamptz, completed_at timestamptz);
create table public.hms_notifications (id uuid primary key default gen_random_uuid(), profile_id uuid references public.profiles(id) on delete cascade,
  account_id uuid references public.communication_accounts(id) on delete cascade, message_id uuid references public.communication_messages(id) on delete cascade);
create table public.donexto_preferences (id uuid primary key default gen_random_uuid(), profile_id uuid references public.profiles(id) on delete cascade);
-- Respaldos (sin FK, como en producción) y un esquema ajeno que NO debe tocarse.
create schema hms_backup_test_20260804;
create table hms_backup_test_20260804.communication_messages (id uuid, account_id uuid);
create table hms_backup_test_20260804.communication_accounts (id uuid, connected_by_profile_id uuid, workspace_id uuid);
create schema otro_esquema;
create table otro_esquema.communication_messages (id uuid, account_id uuid, profile_id uuid);
create schema hms_backupX;  -- no cumple el patrón (mayúscula/sin guion bajo)
create table hms_backupX.profiles (id uuid);

-- Storage mínimo (como en Supabase) y tablas AJENAS con columnas uuid de mismos nombres: NO deben tocarse.
create schema if not exists storage;
create table storage.buckets (id text primary key, name text not null, public boolean default false, created_at timestamptz default now());
create table public.tabla_ajena (id uuid primary key default gen_random_uuid(), user_id uuid, profile_id uuid, account_id uuid,
  workspace_id uuid, message_id uuid, source_message_id uuid);
create table hms_backup_test_20260804.tabla_ajena (user_id uuid, profile_id uuid, account_id uuid, workspace_id uuid, message_id uuid);
