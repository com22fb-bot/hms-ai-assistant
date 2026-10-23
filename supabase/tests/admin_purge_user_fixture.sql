-- Esquema mínimo (copia de FKs/ON DELETE reales, 22 oct 2026) para probar
-- admin_purge_user en un Postgres aislado. Nunca correr contra producción.
create extension if not exists pgcrypto;
create schema if not exists auth;
create table auth.users (id uuid primary key, email text, created_at timestamptz default now());
do $$ begin create role service_role; exception when duplicate_object then null; end $$;
do $$ begin create role anon; exception when duplicate_object then null; end $$;
do $$ begin create role authenticated; exception when duplicate_object then null; end $$;
create table public.admin_allowlist (user_id uuid primary key references auth.users(id) on delete cascade);
create table public.admin_events (id uuid primary key default gen_random_uuid(), occurred_at timestamptz default now(),
  source text, severity text, title text, detail text, status text, created_by text, meta jsonb default '{}');
create table public.profiles (id uuid primary key references auth.users(id) on delete cascade, email text);
create table public.users (id uuid primary key, email text);
create table public.notifications (id serial primary key, user_id uuid references public.users(id));
create table public.workspaces (id uuid primary key default gen_random_uuid(), owner_profile_id uuid references public.profiles(id) on delete set null);
create table public.workspace_members (workspace_id uuid references public.workspaces(id) on delete cascade,
  profile_id uuid references public.profiles(id) on delete cascade);
create table public.communication_accounts (id uuid primary key default gen_random_uuid(),
  workspace_id uuid references public.workspaces(id), connected_by_profile_id uuid references public.profiles(id) on delete set null);
create table public.oauth_credentials (id serial primary key, account_id uuid references public.communication_accounts(id) on delete cascade);
create table public.communication_threads (id uuid primary key default gen_random_uuid(), account_id uuid references public.communication_accounts(id) on delete cascade);
create table public.communication_messages (id uuid primary key default gen_random_uuid(),
  account_id uuid references public.communication_accounts(id) on delete cascade,
  thread_id uuid references public.communication_threads(id) on delete cascade);
create table public.ai_analysis (id serial primary key, message_id uuid references public.communication_messages(id) on delete cascade);
create table public.intelligent_cases (id uuid primary key default gen_random_uuid(),
  workspace_id uuid references public.workspaces(id) on delete cascade, account_id uuid references public.communication_accounts(id) on delete cascade);
create table public.case_messages (id serial primary key, case_id uuid references public.intelligent_cases(id) on delete cascade,
  message_id uuid references public.communication_messages(id) on delete cascade);
create table public.case_events (id serial primary key, case_id uuid references public.intelligent_cases(id) on delete cascade,
  workspace_id uuid references public.workspaces(id) on delete cascade, message_id uuid references public.communication_messages(id) on delete set null);
create table public.system_incidents (id serial primary key, workspace_id uuid references public.workspaces(id) on delete set null,
  account_id uuid references public.communication_accounts(id) on delete set null);
create table public.mail_accounts (id uuid primary key default gen_random_uuid(), user_id uuid references auth.users(id) on delete cascade);
create table public.emails (id uuid primary key default gen_random_uuid(), user_id uuid references auth.users(id) on delete cascade,
  mail_account_id uuid references public.mail_accounts(id) on delete cascade);
create table public.tasks (id serial primary key, user_id uuid references auth.users(id) on delete cascade, email_id uuid references public.emails(id) on delete set null);
create table public.audit_log (id serial primary key, user_id uuid);
create table public.account_plans (user_id uuid primary key references auth.users(id) on delete cascade,
  plan_code text default 'trial', status text default 'trialing', trial_ends_at timestamptz);
