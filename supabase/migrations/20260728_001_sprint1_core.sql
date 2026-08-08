-- ============================================================
-- HMS AI Assistant
-- Sprint 1
-- Core Database
-- ============================================================

create extension if not exists pgcrypto;

-- ============================================================
-- UPDATED_AT
-- ============================================================

create or replace function set_updated_at()
returns trigger
language plpgsql
as $$
begin
    NEW.updated_at = now();
    return NEW;
end;
$$;

-- ============================================================
-- WORKSPACES
-- ============================================================

create table if not exists workspaces (

    id uuid primary key default gen_random_uuid(),

    name text not null,

    slug text unique,

    status text not null default 'active',

    created_at timestamptz not null default now(),

    updated_at timestamptz not null default now()

);

-- ============================================================
-- USERS
-- ============================================================

create table if not exists users (

    id uuid primary key default gen_random_uuid(),

    email text unique not null,

    full_name text,

    password_hash text,

    status text default 'active',

    created_at timestamptz default now(),

    updated_at timestamptz default now()

);

-- ============================================================
-- USER_WORKSPACE
-- ============================================================

create table if not exists user_workspaces (

    id uuid primary key default gen_random_uuid(),

    workspace_id uuid not null references workspaces(id) on delete cascade,

    user_id uuid not null references users(id) on delete cascade,

    role text not null default 'user',

    created_at timestamptz default now(),

    unique(workspace_id,user_id)

);

-- ============================================================
-- COMMUNICATION ACCOUNTS
-- ============================================================

create table if not exists communication_accounts (

    id uuid primary key default gen_random_uuid(),

    workspace_id uuid not null references workspaces(id),

    provider text not null,

    provider_account_id text,

    email text,

    phone text,

    display_name text,

    avatar_url text,

    status text default 'active',

    last_sync_at timestamptz,

    created_at timestamptz default now(),

    updated_at timestamptz default now()

);

create index if not exists idx_accounts_provider
on communication_accounts(provider);

create index if not exists idx_accounts_workspace
on communication_accounts(workspace_id);

-- ============================================================
-- OAUTH
-- ============================================================

create table if not exists oauth_credentials (

    id uuid primary key default gen_random_uuid(),

    account_id uuid not null
        references communication_accounts(id)
        on delete cascade,

    access_token text,

    refresh_token text,

    expires_at timestamptz,

    token_uri text,

    scopes jsonb default '[]',

    metadata jsonb default '{}',

    created_at timestamptz default now(),

    updated_at timestamptz default now(),

    unique(account_id)

);

-- ============================================================
-- OAUTH STATES
-- ============================================================

create table if not exists oauth_states (

    state text primary key,

    provider text not null,

    expires_at timestamptz not null,

    created_at timestamptz default now()

);

-- ============================================================
-- THREADS
-- ============================================================

create table if not exists communication_threads (

    id uuid primary key default gen_random_uuid(),

    account_id uuid
        references communication_accounts(id)
        on delete cascade,

    provider text,

    external_thread_id text,

    subject text,

    participants text,

    last_message_at timestamptz,

    created_at timestamptz default now(),

    updated_at timestamptz default now(),

    unique(account_id,external_thread_id)

);

-- ============================================================
-- MESSAGES
-- ============================================================

create table if not exists communication_messages (

    id uuid primary key default gen_random_uuid(),

    thread_id uuid
        references communication_threads(id)
        on delete cascade,

    account_id uuid
        references communication_accounts(id)
        on delete cascade,

    provider text,

    external_message_id text,

    sender text,

    recipients jsonb,

    cc jsonb,

    bcc jsonb,

    subject text,

    body_text text,

    body_html text,

    received_at timestamptz,

    has_attachments boolean default false,

    ai_processed boolean default false,

    created_at timestamptz default now(),

    unique(account_id,external_message_id)

);

create index if not exists idx_messages_received
on communication_messages(received_at desc);

-- ============================================================
-- ATTACHMENTS
-- ============================================================

create table if not exists attachments (

    id uuid primary key default gen_random_uuid(),

    message_id uuid
        references communication_messages(id)
        on delete cascade,

    filename text,

    mime_type text,

    size bigint,

    storage_path text,

    created_at timestamptz default now()

);

-- ============================================================
-- AI ANALYSIS
-- ============================================================

create table if not exists ai_analysis (

    id uuid primary key default gen_random_uuid(),

    message_id uuid
        references communication_messages(id)
        on delete cascade,

    summary text,

    sentiment text,

    priority text,

    category text,

    requires_reply boolean default false,

    confidence numeric(5,2),

    entities jsonb default '{}',

    deadline timestamptz,

    created_at timestamptz default now(),

    unique(message_id)

);

-- ============================================================
-- TASKS
-- ============================================================

create table if not exists tasks (

    id uuid primary key default gen_random_uuid(),

    workspace_id uuid
        references workspaces(id),

    message_id uuid
        references communication_messages(id),

    assigned_user uuid
        references users(id),

    title text,

    description text,

    status text default 'pending',

    priority text default 'normal',

    due_date timestamptz,

    completed_at timestamptz,

    created_at timestamptz default now(),

    updated_at timestamptz default now()

);

-- ============================================================
-- REMINDERS
-- ============================================================

create table if not exists reminders (

    id uuid primary key default gen_random_uuid(),

    task_id uuid
        references tasks(id)
        on delete cascade,

    remind_at timestamptz,

    sent boolean default false,

    created_at timestamptz default now()

);

-- ============================================================
-- NOTIFICATIONS
-- ============================================================

create table if not exists notifications (

    id uuid primary key default gen_random_uuid(),

    user_id uuid
        references users(id),

    channel text,

    title text,

    body text,

    delivered boolean default false,

    created_at timestamptz default now()

);

-- ============================================================
-- AUDIT
-- ============================================================

create table if not exists audit_log (

    id uuid primary key default gen_random_uuid(),

    user_id uuid,

    action text,

    entity text,

    entity_id text,

    old_values jsonb,

    new_values jsonb,

    ip text,

    created_at timestamptz default now()

);

-- ============================================================
-- TRIGGERS
-- ============================================================

create trigger trg_workspace_updated
before update on workspaces
for each row
execute function set_updated_at();

create trigger trg_users_updated
before update on users
for each row
execute function set_updated_at();

create trigger trg_accounts_updated
before update on communication_accounts
for each row
execute function set_updated_at();

create trigger trg_threads_updated
before update on communication_threads
for each row
execute function set_updated_at();

create trigger trg_tasks_updated
before update on tasks
for each row
execute function set_updated_at();

create trigger trg_oauth_updated
before update on oauth_credentials
for each row
execute function set_updated_at();