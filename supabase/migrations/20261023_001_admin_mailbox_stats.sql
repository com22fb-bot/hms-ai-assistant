-- Conteo real de correos guardados por buzón y por usuario (solo admin vía service_role).
-- Solo lectura: agrega con GROUP BY (sin N+1, sin cuerpos ni asuntos).
-- Usuario -> communication_accounts.connected_by_profile_id -> communication_accounts.id -> communication_messages.account_id
create or replace function public.admin_mailbox_stats(p_profile_ids uuid[])
returns table (
  profile_id uuid,
  account_id uuid,
  provider text,
  mailbox_email text,
  status text,
  last_sync_at timestamptz,
  messages bigint
)
language sql
stable
security definer
set search_path = public
as $$
  select a.connected_by_profile_id, a.id, a.provider, a.email, a.status, a.last_sync_at,
         coalesce(m.n, 0)::bigint
  from public.communication_accounts a
  left join (
    select account_id, count(*) as n
    from public.communication_messages
    where account_id in (select id from public.communication_accounts
                         where connected_by_profile_id = any(p_profile_ids))
    group by account_id
  ) m on m.account_id = a.id
  where a.connected_by_profile_id = any(p_profile_ids);
$$;

revoke all on function public.admin_mailbox_stats(uuid[]) from public, anon, authenticated;
grant execute on function public.admin_mailbox_stats(uuid[]) to service_role;
