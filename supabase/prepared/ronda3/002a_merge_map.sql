-- RONDA 3 · PREPARADA · NO APLICAR SIN APROBACIÓN (requiere 000_ops_infra.sql)
-- Fase A1: mapa canónico + línea base. Solo crea tablas ops_r3_*; no toca datos.
-- Revisar ops_r3_merge_map ANTES de 002b. Solo filas con canónica y approved=true
-- entran a la consolidación automática; el resto es revisión manual (ver README).
begin;
create table if not exists public.ops_r3_merge_map (
  old_account_id uuid primary key,
  canonical_account_id uuid,
  provider text not null,
  provider_account_id text not null,
  old_status text not null,
  reason text not null,      -- huerfana_con_canonica | revision_manual_sin_canonica
  approved boolean not null default false,
  approved_by text,
  created_at timestamptz not null default now(),
  constraint ops_r3_auto_requires_canonical
    check (not approved or canonical_account_id is not null)
);
alter table public.ops_r3_merge_map enable row level security;

with live_ws as (
  select distinct workspace_id from public.workspace_members
  where status = 'active' and deleted_at is null
), acc as (
  select a.*, (a.workspace_id in (select workspace_id from live_ws)) as live
  from public.communication_accounts a
  where a.provider_account_id is not null
), grp as (
  select provider, provider_account_id,
         count(*) filter (where live) as live_rows,
         (array_agg(id order by created_at desc) filter (where live))[1] as live_id
  from acc group by 1, 2 having count(*) > 1
)
insert into public.ops_r3_merge_map
  (old_account_id, canonical_account_id, provider, provider_account_id, old_status, reason)
select a.id,
       case when g.live_rows = 1 then g.live_id end,
       a.provider, a.provider_account_id, coalesce(a.status, 'null'),
       case when g.live_rows = 1 then 'huerfana_con_canonica' else 'revision_manual_sin_canonica' end
from acc a join grp g using (provider, provider_account_id)
where not a.live            -- nunca se mapean filas de workspaces con miembros
  and g.live_rows <= 1      -- grupos con 2+ filas vivas (usuarios distintos) quedan fuera
on conflict (old_account_id) do nothing;

create table if not exists public.ops_r3_baseline as
select a.id as account_id,
       (select count(*) from public.communication_messages m where m.account_id = a.id) as messages,
       (select count(*) from public.communication_threads t where t.account_id = a.id) as threads,
       (select count(*) from public.intelligent_cases c where c.account_id = a.id) as cases,
       now() as taken_at
from public.communication_accounts a
where a.id in (select old_account_id from public.ops_r3_merge_map
               union select canonical_account_id from public.ops_r3_merge_map
               where canonical_account_id is not null);
alter table public.ops_r3_baseline enable row level security;
commit;
