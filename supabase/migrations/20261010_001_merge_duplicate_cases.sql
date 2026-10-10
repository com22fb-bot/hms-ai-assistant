-- Backfill único: une casos abiertos duplicados del mismo usuario (workspace).
-- Misma clave = mismo asunto normalizado, o misma marca + aviso de seguridad
-- en 7 días. Conserva el caso más antiguo; mueve mensajes, eventos,
-- participantes y avisos; los duplicados quedan 'closed' con metadata.merged_into.
-- No borra mensajes ni casos.
do $$
declare
  r record;
  keep_id uuid;
begin
  for r in
    with open_cases as (
      select c.*,
        coalesce(
          c.metadata->>'event_key',
          case when c.title ~* '(alerta de seguridad|security alert|nuevo dispositivo|new sign-?in)'
               then lower(split_part(split_part(coalesce(c.requester_email,''),'@',2),'.',
                    greatest(array_length(string_to_array(split_part(coalesce(c.requester_email,''),'@',2),'.'),1)-1,1)))
                    || ':security_alert'
          end,
          'subject:' || c.normalized_subject
        ) as gkey
      from intelligent_cases c
      where c.status in ('new','analyzing','in_progress','delegated','waiting_internal','waiting_external')
    )
    select workspace_id, gkey, array_agg(id order by opened_at, created_at) ids
    from open_cases
    where gkey is not null and gkey <> 'subject:'
    group by workspace_id, gkey
    having count(*) > 1
  loop
    keep_id := r.ids[1];
    update case_messages set case_id = keep_id where case_id = any(r.ids[2:]);
    update case_events set case_id = keep_id where case_id = any(r.ids[2:]);
    update case_participants p set case_id = keep_id
      where p.case_id = any(r.ids[2:])
        and not exists (select 1 from case_participants q where q.case_id = keep_id and q.email = p.email);
    update case_notifications set case_id = keep_id where case_id = any(r.ids[2:]);
    update intelligent_cases k set
      source_count = (select sum(source_count) from intelligent_cases where id = any(r.ids)),
      last_activity_at = (select max(last_activity_at) from intelligent_cases where id = any(r.ids))
    where k.id = keep_id;
    update intelligent_cases set status = 'closed', closed_at = now(),
      metadata = metadata || jsonb_build_object('merged_into', keep_id, 'merged_by', 'backfill_2026_10_10')
    where id = any(r.ids[2:]);
    raise notice 'merged % into %', array_length(r.ids,1)-1, keep_id;
  end loop;
end $$;
