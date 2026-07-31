-- ============================================================
-- HMS AI Assistant
-- Sprint 4.3 — Intelligent Case Engine
-- Fecha: 2026-07-31
-- ============================================================

create extension if not exists pgcrypto;

-- ------------------------------------------------------------
-- METADATOS DE CORRELACIÓN PARA MENSAJES
-- ------------------------------------------------------------

alter table public.communication_messages
    add column if not exists normalized_subject text;

alter table public.communication_messages
    add column if not exists direction text
        not null default 'inbound';

alter table public.communication_messages
    add column if not exists internet_message_id text;

alter table public.communication_messages
    add column if not exists in_reply_to text;

alter table public.communication_messages
    add column if not exists references_header jsonb
        not null default '[]'::jsonb;

alter table public.communication_messages
    add column if not exists correlation_key text;

alter table public.communication_messages
    add column if not exists case_processed boolean
        not null default false;

alter table public.communication_messages
    add column if not exists processed_at timestamptz;

alter table public.communication_messages
    add column if not exists updated_at timestamptz
        not null default now();

do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname = 'communication_messages_direction_check'
    ) then
        alter table public.communication_messages
            add constraint communication_messages_direction_check
            check (direction in ('inbound', 'outbound', 'draft', 'system'));
    end if;
end $$;

create index if not exists idx_messages_case_processing
    on public.communication_messages(account_id, case_processed, received_at);

create index if not exists idx_messages_normalized_subject
    on public.communication_messages(account_id, normalized_subject);

create index if not exists idx_messages_internet_message_id
    on public.communication_messages(account_id, internet_message_id);

-- ------------------------------------------------------------

-- DATOS EXISTENTES
-- ------------------------------------------------------------

update public.communication_messages
set
    direction = case
        when labels ? 'SENT' then 'outbound'
        when labels ? 'DRAFT' then 'draft'
        else 'inbound'
    end,
    case_processed = false
where true;
