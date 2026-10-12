-- Solo SELECT. Cada fila debe dar ok = true.
select 'V1' v, m.canonical_account_id::text k, (
  select count(distinct x.external_message_id) from public.communication_messages x
  where x.account_id = m.canonical_account_id) =
  (select count(distinct x.external_message_id) from public.communication_messages x
   where x.account_id = m.canonical_account_id
      or x.account_id in (select old_account_id from public.ops_r3_merge_map z
                          where z.canonical_account_id = m.canonical_account_id and z.approved)) ok
from (select distinct canonical_account_id from public.ops_r3_merge_map
      where approved and canonical_account_id is not null) m
union all
select 'V1b', m.canonical_account_id::text, (
  select count(distinct x.external_thread_id) from public.communication_threads x
  where x.account_id = m.canonical_account_id) =
  (select count(distinct x.external_thread_id) from public.communication_threads x
   where x.account_id = m.canonical_account_id
      or x.account_id in (select old_account_id from public.ops_r3_merge_map z
                          where z.canonical_account_id = m.canonical_account_id and z.approved))
from (select distinct canonical_account_id from public.ops_r3_merge_map
      where approved and canonical_account_id is not null) m
union all
-- V2: ninguna cuenta aprobada sigue activa en workspace sin miembros
select 'V2', null, not exists (
  select 1 from public.communication_accounts a
  join public.ops_r3_merge_map m on m.old_account_id = a.id and m.approved
  where a.status = 'active')
union all
-- V3: sin credenciales en cuentas retiradas; filas sin canónica conservan las suyas
select 'V3', null, not exists (
  select 1 from public.oauth_credentials o join public.communication_accounts a on a.id = o.account_id
  where a.status = 'superseded')
union all
select 'V3b', m.old_account_id::text,
  (select status from public.communication_accounts where id = m.old_account_id) = m.old_status
from public.ops_r3_merge_map m where m.canonical_account_id is null
union all
-- V4: cada caso de copia aprobada quedó mapeado; cada evento, participante, vínculo
-- y notificación tiene equivalente en el caso destino
select 'V4', null, not exists (
  select 1 from public.intelligent_cases c join public.ops_r3_merge_map m
    on m.old_account_id = c.account_id and m.approved and m.canonical_account_id is not null
  where c.id not in (select old_case_id from public.ops_r3_case_map))
union all
select 'V4e', null, not exists (
  select 1 from public.case_events e join public.ops_r3_case_map cm on cm.old_case_id = e.case_id
  where e.id not in (select old_event_id from public.ops_r3_event_map))
union all
select 'V4p', null, not exists (
  select 1 from public.case_participants p join public.ops_r3_case_map cm on cm.old_case_id = p.case_id
  where not exists (select 1 from public.case_participants q
                    where q.case_id = cm.new_case_id and lower(q.email) = lower(p.email)))
union all
select 'V4l', null, not exists (
  select 1 from public.case_messages x join public.ops_r3_case_map cm on cm.old_case_id = x.case_id
  join public.communication_messages om on om.id = x.message_id
  join public.ops_r3_merge_map mm on mm.old_account_id = om.account_id
  where not exists (select 1 from public.case_messages y join public.communication_messages k on k.id = y.message_id
                    where k.account_id = mm.canonical_account_id and k.external_message_id = om.external_message_id))
union all
select 'V4n', null, not exists (
  select 1 from public.case_notifications n join public.ops_r3_case_map cm on cm.old_case_id = n.case_id
  where not exists (select 1 from public.case_notifications q where q.case_id = cm.new_case_id
                    and q.channel = n.channel and q.level = n.level and q.title = n.title
                    and q.created_at = n.created_at))
union all
-- V5: las copias no perdieron nada (purga diferida)
select 'V5', b.account_id::text,
  (select count(*) from public.communication_messages x where x.account_id = b.account_id) = b.messages
  and (select count(*) from public.communication_threads x where x.account_id = b.account_id) = b.threads
  and (select count(*) from public.intelligent_cases x where x.account_id = b.account_id) = b.cases
from public.ops_r3_baseline b
where b.account_id in (select old_account_id from public.ops_r3_merge_map);
