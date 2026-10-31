-- PROPUESTA CONC-01 — NO APLICAR sin autorización de ASTRA. Fuera de supabase/migrations a propósito.
-- La corrección del PR funciona sin esquema nuevo; esto añade defensa en la BD.
-- 1) Un solo caso por mensaje origen (evita casos huérfanos duplicados aun con carreras).
--    Antes de crear: verificar 0 duplicados:
--    select metadata->>'source_message_id', count(*) from intelligent_cases
--     where metadata ? 'source_message_id' group by 1 having count(*) > 1;
create unique index concurrently if not exists idx_intelligent_cases_source_message
    on public.intelligent_cases ((metadata->>'source_message_id'))
    where metadata ? 'source_message_id';
-- 2) Reclamación explícita en vez de reutilizar triage_category (opcional, fase 2).
alter table public.communication_messages
    add column if not exists case_claimed_at timestamptz,
    add column if not exists case_claim_attempts smallint not null default 0;
create index if not exists idx_comm_messages_pending_claim
    on public.communication_messages (account_id, received_at desc)
    where case_processed = false;
