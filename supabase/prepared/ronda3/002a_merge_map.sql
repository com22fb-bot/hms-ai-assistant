-- RONDA 3 · PREPARADA · NO APLICAR SIN APROBACIÓN
-- Fase A1: construir el mapa canónico + línea base. Solo crea tablas ops_r3_*;
-- no toca datos de producto. Revisar ops_r3_merge_map ANTES de ejecutar 002b.
begin;
create table if not exists public.ops_r3_merge_map (
  old_account_id uuid primary key,
  canonical_account_id uuid,
  provider text not null,
  provider_account_id text not null,
  old_status text not null,
  reason text not null,
  approved boolean not null default false,
  created_at timestamptz not null default now()
);

with live_ws as (
  select distinct workspace_id from public.workspace_members where status = 'active'
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
       case when g.live_rows = 1 then 'huerfana_con_canonica'
            when g.live_rows = 0 then 'huerfana_sin_canonica'
            else 'ambigua_revisar' end
from acc a join grp g using (provider, provider_account_id)
where not a.live            -- nunca se mapean filas de workspaces con miembros
  and g.live_rows <= 1      -- grupos ambiguos (2+ vivas) se dejan fuera
on conflict (old_account_id) do nothing;

create table if not exists public.ops_r3_baseline as
select a.id as account_id,
       (select count(*) from public.communication_messages m where m.account_id = a.id) as messages,
       (select count(*) from public.communication_threads t where t.account_id = a.id) as threads,
       (select count(*) from public.intelligent_cases c where c.account_id = a.id) as cases,
       (select count(*) from public.case_messages cm join public.intelligent_cases c on c.id = cm.case_id
         where c.account_id = a.id) as case_messages,
       (select count(*) from public.donexto_preferences) as preferences_total,
       now() as taken_at
from public.communication_accounts a
where a.id in (select old_account_id from public.ops_r3_merge_map
               union select canonical_account_id from public.ops_r3_merge_map
               where canonical_account_id is not null);
commit;
-- Revisión humana: select * from ops_r3_merge_map order by provider_account_id;
-- Aprobar:          update ops_r3_merge_map set approved = true where ...;
