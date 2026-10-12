-- Solo SELECT. Cada fila debe dar ok = true.
-- V1: la canónica tiene todos los mensajes únicos del grupo
select 'V1' v, m.canonical_account_id, (
  select count(distinct x.external_message_id) from public.communication_messages x
  where x.account_id = m.canonical_account_id) =
  (select count(distinct x.external_message_id) from public.communication_messages x
   where x.account_id = m.canonical_account_id
      or x.account_id in (select old_account_id from public.ops_r3_merge_map z
                          where z.canonical_account_id = m.canonical_account_id and z.approved)) ok
from (select distinct canonical_account_id from public.ops_r3_merge_map
      where approved and canonical_account_id is not null) m
union all
-- V1b: hilos únicos
select 'V1b', m.canonical_account_id, (
  select count(distinct x.external_thread_id) from public.communication_threads x
  where x.account_id = m.canonical_account_id) =
  (select count(distinct x.external_thread_id) from public.communication_threads x
   where x.account_id = m.canonical_account_id
      or x.account_id in (select old_account_id from public.ops_r3_merge_map z
                          where z.canonical_account_id = m.canonical_account_id and z.approved))
from (select distinct canonical_account_id from public.ops_r3_merge_map
      where approved and canonical_account_id is not null) m
union all
-- V2: ninguna cuenta activa en workspace sin miembros activos
select 'V2', null, not exists (
  select 1 from public.communication_accounts a where a.status = 'active'
    and not exists (select 1 from public.workspace_members w
                    where w.workspace_id = a.workspace_id and w.status = 'active'))
union all
-- V3: sin credenciales en cuentas retiradas
select 'V3', null, not exists (
  select 1 from public.oauth_credentials o join public.communication_accounts a on a.id = o.account_id
  where a.status = 'superseded')
union all
-- V4: casos y vínculos de la canónica >= antes, y cada caso de copia quedó mapeado
select 'V4', b.account_id,
  (select count(*) from public.intelligent_cases c where c.account_id = b.account_id) >= b.cases
  and (select count(*) from public.case_messages cm join public.intelligent_cases c on c.id = cm.case_id
       where c.account_id = b.account_id) >= b.case_messages
from public.ops_r3_baseline b
where b.account_id in (select canonical_account_id from public.ops_r3_merge_map)
union all
select 'V4b', null, not exists (
  select 1 from public.intelligent_cases c join public.ops_r3_merge_map m
    on m.old_account_id = c.account_id and m.approved and m.canonical_account_id is not null
  where c.id not in (select old_case_id from public.ops_r3_case_map))
union all
-- V5: las copias no perdieron nada (purga diferida) y preferencias intactas
select 'V5', b.account_id,
  (select count(*) from public.communication_messages x where x.account_id = b.account_id) = b.messages
  and (select count(*) from public.communication_threads x where x.account_id = b.account_id) = b.threads
  and (select count(*) from public.intelligent_cases x where x.account_id = b.account_id) = b.cases
  and (select count(*) from public.donexto_preferences) = b.preferences_total
from public.ops_r3_baseline b
where b.account_id in (select old_account_id from public.ops_r3_merge_map);
