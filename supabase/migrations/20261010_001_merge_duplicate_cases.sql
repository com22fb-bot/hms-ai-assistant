-- Backfill único: une casos abiertos del MISMO evento del mismo usuario.
-- Solo eventos con clave explícita: metadata.event_key, o aviso de seguridad
-- con marca = dominio registrable del remitente (accounts.google.com → google,
-- e.bbva.com.mx → bbva). Ventana: 7 días entre avisos consecutivos (1 día para
-- códigos). Conserva el caso más antiguo de cada racha; mueve mensajes,
-- eventos, participantes y avisos; los demás quedan 'closed' con
-- metadata.merged_into. No borra mensajes ni casos.
create or replace function pg_temp.brand_of(addr text) returns text language sql immutable as $$
  with d as (select string_to_array(lower(split_part(coalesce(addr,''),'@',2)),'.') as parts),
  t as (  -- quita TLD y segundo nivel genérico (com.mx, co.uk)
    select case
      when array_length(parts,1) >= 3 and parts[array_length(parts,1)-1] in ('com','co','net','org','gob','gov','edu','ac')
        then parts[1:array_length(parts,1)-2]
      when array_length(parts,1) >= 2 then parts[1:array_length(parts,1)-1]
      else parts end as p
    from d)
  select nullif(p[array_length(p,1)], '') from t
$$;

do $$
declare
  r record;
  keep_id uuid;
begin
  for r in
    with keyed as (
      select c.id, c.workspace_id, c.opened_at, c.created_at,
        coalesce(
          c.metadata->>'event_key',
          case when c.title ~* '(alerta de seguridad|security alert|nuevo dispositivo|new sign-?in|actividad (inusual|sospechosa))'
                and pg_temp.brand_of(c.requester_email) is not null
               then pg_temp.brand_of(c.requester_email) || ':security_alert' end
        ) as gkey
      from intelligent_cases c
      where c.status in ('new','analyzing','in_progress','delegated','waiting_internal','waiting_external')
    ),
    ordered as (
      select *, lag(opened_at) over (partition by workspace_id, gkey order by opened_at, created_at) as prev_at
      from keyed where gkey is not null
    ),
    runs as (
      select *, sum(case when prev_at is null
                          or opened_at - prev_at > (case when gkey like '%:verification_code' then interval '1 day' else interval '7 days' end)
                         then 1 else 0 end)
                over (partition by workspace_id, gkey order by opened_at, created_at) as run_no
      from ordered
    )
    select workspace_id, gkey, run_no, array_agg(id order by opened_at, created_at) ids
    from runs
    group by workspace_id, gkey, run_no
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
      last_activity_at = (select max(last_activity_at) from intelligent_cases where id = any(r.ids)),
      metadata = k.metadata || jsonb_build_object('event_key', r.gkey)
    where k.id = keep_id;
    update intelligent_cases set status = 'closed', closed_at = now(),
      metadata = metadata || jsonb_build_object('merged_into', keep_id, 'merged_by', 'backfill_2026_10_10')
    where id = any(r.ids[2:]);
  end loop;
end $$;
