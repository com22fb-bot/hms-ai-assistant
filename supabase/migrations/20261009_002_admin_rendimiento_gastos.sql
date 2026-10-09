-- Panel /admin: estadísticas de la base y gastos de operación.
-- Solo service_role (el backend). RLS activo y sin políticas = nadie más.

create table if not exists public.admin_expenses (
  id uuid primary key default gen_random_uuid(),
  servicio text not null,
  plan text not null default '',
  monto numeric(12,2) not null default 0,
  moneda text not null default 'USD' check (moneda in ('USD','MXN')),
  periodicidad text not null default 'mensual' check (periodicidad in ('mensual','anual','unico')),
  proximo_cobro date,
  notas text not null default '',
  activo boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
alter table public.admin_expenses enable row level security;
revoke all on public.admin_expenses from anon, authenticated;

create table if not exists public.admin_settings (
  key text primary key,
  value text not null,
  updated_at timestamptz not null default now()
);
alter table public.admin_settings enable row level security;
revoke all on public.admin_settings from anon, authenticated;

insert into public.admin_settings (key, value) values ('usd_mxn', '18.50')
on conflict (key) do nothing;

insert into public.admin_expenses (servicio, plan, monto, moneda, periodicidad, proximo_cobro, notas, activo)
select * from (values
  ('Cursor', 'Pro', 20.00, 'USD', 'mensual', null::date, 'Incluye Grok Bot. Revisa la fecha de renovación y escríbela aquí.', true),
  ('SuperGrok', 'Lite', 10.00, 'USD', 'unico', null::date, 'Pago único del 7 oct 2026 (recibo #2160-2883). No incluye Grok Bot. Reembolso solicitado (f02f17ff-8e89-4f82-bfca-09cbd514ec6c).', false),
  ('Supabase', 'Free', 0.00, 'USD', 'mensual', null::date, 'Recomendado: Pro US$25/mes antes de lanzar (respaldos diarios y sin pausas).', true),
  ('Railway', 'Por confirmar', 0.00, 'USD', 'mensual', null::date, 'Plan y monto por confirmar en railway.com > Billing.', true),
  ('Cloudflare', 'Free', 0.00, 'USD', 'mensual', null::date, 'Zona donexto.com en plan Free Website.', true),
  ('Dominio donexto.com', 'Cloudflare Registrar', 0.00, 'USD', 'anual', null::date, 'Monto y fecha de renovación por confirmar en Cloudflare > Domain Registration.', true),
  ('Resend', 'Por confirmar', 0.00, 'USD', 'mensual', null::date, 'Correos del sistema. Plan por confirmar en resend.com > Billing.', true),
  ('Figma', 'Starter', 0.00, 'USD', 'mensual', null::date, 'Tablero de pendientes en FigJam.', true),
  ('GitHub', 'Free', 0.00, 'USD', 'mensual', null::date, '', true),
  ('OpenAI', 'Por confirmar', 0.00, 'USD', 'mensual', null::date, 'Solo borradores del admin. Monto por confirmar en platform.openai.com > Usage.', true)
) as seed(servicio, plan, monto, moneda, periodicidad, proximo_cobro, notas, activo)
where not exists (select 1 from public.admin_expenses);

create or replace function public.admin_db_stats()
returns jsonb
language plpgsql
security definer
set search_path = public, pg_catalog
as $$
declare
  result jsonb;
  slow jsonb := null;
begin
  select jsonb_build_object(
    'db_size_bytes', pg_database_size(current_database()),
    'emails_total', (select count(*) from public.communication_messages),
    'emails_first_at', (select min(created_at) from public.communication_messages),
    'emails_last_30d', (select count(*) from public.communication_messages where created_at > now() - interval '30 days'),
    'mailboxes_active', (select count(*) from public.communication_accounts where status = 'active'),
    'mailboxes_total', (select count(*) from public.communication_accounts),
    'users_total', (select count(*) from auth.users),
    'users_active_30d', (select count(*) from auth.users where last_sign_in_at > now() - interval '30 days'),
    'connections_active', (select count(*) from pg_stat_activity where datname = current_database() and state = 'active'),
    'connections_total', (select count(*) from pg_stat_activity where datname = current_database()),
    'top_tables', (
      select coalesce(jsonb_agg(t order by t.bytes desc), '[]'::jsonb) from (
        select c.relname as name, pg_total_relation_size(c.oid) as bytes
        from pg_class c join pg_namespace n on n.oid = c.relnamespace
        where n.nspname = 'public' and c.relkind = 'r'
        order by pg_total_relation_size(c.oid) desc limit 6
      ) t)
  ) into result;

  begin
    execute $q$
      select coalesce(jsonb_agg(s), '[]'::jsonb) from (
        select left(regexp_replace(query, '\s+', ' ', 'g'), 140) as query,
               calls, round(mean_exec_time::numeric, 1) as mean_ms,
               round(total_exec_time::numeric / 1000, 1) as total_s
        from extensions.pg_stat_statements
        where dbid = (select oid from pg_database where datname = current_database())
          and query not ilike '%pg_stat_statements%'
        order by mean_exec_time desc limit 5) s
    $q$ into slow;
  exception when others then
    slow := null;
  end;

  return result || jsonb_build_object('slow_queries', slow);
end;
$$;

revoke all on function public.admin_db_stats() from public, anon, authenticated;
grant execute on function public.admin_db_stats() to service_role;
