-- Bitácora de eventos del panel /admin (caídas de proveedores, despliegues,
-- respaldos, alertas y cambios manuales). Aditiva: no toca tablas existentes.
-- admin_allowlist se carga fuera del repositorio (no se publican correos ni IDs).

create table if not exists public.admin_allowlist (
  user_id uuid primary key references auth.users(id) on delete cascade,
  created_at timestamptz not null default now()
);
alter table public.admin_allowlist enable row level security;
revoke all on public.admin_allowlist from anon, authenticated;

create or replace function public.is_donexto_admin()
returns boolean
language sql
stable
security definer
set search_path = public, pg_catalog
as $$
  select exists (select 1 from public.admin_allowlist where user_id = auth.uid());
$$;
revoke all on function public.is_donexto_admin() from public, anon;
grant execute on function public.is_donexto_admin() to authenticated;

create table if not exists public.admin_events (
  id uuid primary key default gen_random_uuid(),
  occurred_at timestamptz not null default now(),
  ended_at timestamptz,
  source text not null default 'manual'
    check (source in ('railway','cloudflare','supabase','github','backup','monitor','deploy','manual')),
  severity text not null default 'info'
    check (severity in ('info','aviso','grave','critico')),
  title text not null check (length(title) between 1 and 200),
  detail text not null default '',
  status text not null default 'abierto' check (status in ('abierto','resuelto')),
  created_by text not null default 'manual',
  -- Datos estructurados (respaldos: kind, result, size_bytes, duration_s, verified, run_url).
  meta jsonb not null default '{}'::jsonb,
  -- Clave idempotente opcional (p. ej. gh-run-<id>) para no duplicar eventos.
  external_id text unique,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists admin_events_occurred_idx on public.admin_events (occurred_at desc);
create index if not exists admin_events_source_idx on public.admin_events (source, occurred_at desc);

alter table public.admin_events enable row level security;
revoke all on public.admin_events from anon;
grant select, insert, update on public.admin_events to authenticated;

drop policy if exists admin_events_select on public.admin_events;
create policy admin_events_select on public.admin_events
  for select to authenticated using (public.is_donexto_admin());
drop policy if exists admin_events_insert on public.admin_events;
create policy admin_events_insert on public.admin_events
  for insert to authenticated with check (public.is_donexto_admin());
drop policy if exists admin_events_update on public.admin_events;
create policy admin_events_update on public.admin_events
  for update to authenticated using (public.is_donexto_admin()) with check (public.is_donexto_admin());
-- Sin política de DELETE: la bitácora no se borra desde el panel.

create or replace function public.admin_events_touch()
returns trigger language plpgsql set search_path = public, pg_catalog as $$
begin
  new.updated_at := now();
  return new;
end;
$$;
drop trigger if exists admin_events_touch on public.admin_events;
create trigger admin_events_touch before update on public.admin_events
  for each row execute function public.admin_events_touch();

insert into public.admin_events (occurred_at, source, severity, title, detail, status, created_by, external_id)
values ('2026-10-21 16:00:00-06'::timestamptz, 'railway', 'grave',
  'Railway: despliegues pausados por falla del proveedor',
  'Falla mayor de Railway: "Deploys have been paused temporarily". Hora de inicio aproximada (16:00 CDMX), primer registro conocido de la rutina de reintento. La API sigue sana en 2624a20. PR #168 (3a57992) ya está en main y espera despliegue; la rutina "Desplegar PR 168 en Railway" reintenta cada 30 minutos.',
  'abierto', 'grok-bot', 'railway-2026-10-21-deploys-pausados')
on conflict (external_id) do nothing;
