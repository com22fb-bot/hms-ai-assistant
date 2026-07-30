-- ============================================================
-- HMS AI Assistant
-- Sprint 4.4
-- Metadatos de Gmail requeridos por la bandeja
-- ============================================================

alter table public.communication_messages
    add column if not exists labels jsonb
        not null
        default '[]'::jsonb;

alter table public.communication_messages
    add column if not exists is_unread boolean
        not null
        default false;

alter table public.communication_messages
    add column if not exists snippet text;

create index if not exists idx_messages_account_received
    on public.communication_messages(
        account_id,
        received_at desc
    );

create index if not exists idx_messages_account_unread
    on public.communication_messages(
        account_id,
        is_unread
    );
