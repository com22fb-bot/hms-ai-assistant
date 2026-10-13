-- Ronda 3 · a lo sumo un buzón vivo por proveedor + dirección normalizada.
-- address_key = lower(btrim(email)) o, si no hay email, lower(btrim(provider_account_id)).
-- La API reutiliza o mueve esa fila al reconectar (oauth_storage.upsert_communication_account)
-- y, si dos conexiones chocan con el índice (23505), relee y actualiza.
-- Rollback: drop index if exists public.ux_comm_accounts_live_address;
--           alter table public.communication_accounts drop column if exists address_key;
begin;
alter table public.communication_accounts
  add column if not exists address_key text
  generated always as (lower(btrim(coalesce(nullif(btrim(email), ''), provider_account_id)))) stored;

create unique index if not exists ux_comm_accounts_live_address
  on public.communication_accounts (provider, address_key)
  where status in ('active', 'needs_reauth');
commit;
