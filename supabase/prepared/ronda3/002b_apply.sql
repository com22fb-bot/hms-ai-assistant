-- RONDA 3 · PREPARADA · NO APLICAR SIN APROBACIÓN (requiere 000 y 002a)
-- Solo filas approved = true CON canónica. Filas sin canónica no pierden credenciales
-- ni cambian de estado (revisión manual).
-- Identidad de caso (sin fusiones por asunto/título):
--   A) mismo event_key no nulo Y mismo hilo del proveedor (external_thread_id), o
--   B) el mismo conjunto no vacío de external_message_id vinculados.
--   1 candidato => se fusiona; 0 => se copia como caso nuevo; 2+ => ambiguo, se copia aparte.
-- En la fusión se agregan, sin duplicar, eventos, participantes, vínculos y notificaciones.
-- Toda inserción/actualización/borrado queda en ops_r3_rows con op_id y hash.
begin;
create table if not exists public.ops_r3_case_map (
  op_id uuid not null, old_case_id uuid not null, new_case_id uuid not null,
  decision text not null,   -- fusionado | copiado | copiado_ambiguo
  primary key (op_id, old_case_id));
create table if not exists public.ops_r3_event_map (
  op_id uuid not null, old_event_id uuid not null, new_event_id uuid not null,
  primary key (op_id, old_event_id));
alter table public.ops_r3_case_map enable row level security;
alter table public.ops_r3_event_map enable row level security;

do $$
declare
  v_op uuid; r record; c record; e record; p record; n record; cm record;
  v_cols text; v_sel text; v_target uuid; v_ncand int; v_decision text; v_new uuid;
  v_src_set text[]; v_src_thread text; v_msg uuid; v_ev uuid; v_id uuid;
begin
  if exists (select 1 from public.message_classification_rules x
             join public.ops_r3_merge_map m on m.old_account_id = x.account_id and m.approved)
     or exists (select 1 from public.message_watch_rules x
             join public.ops_r3_merge_map m on m.old_account_id = x.account_id and m.approved) then
    raise exception 'Hay reglas en cuentas a retirar: revisión manual requerida';
  end if;
  insert into public.ops_r3_operation (script) values ('002b_apply') returning op_id into v_op;

  select string_agg(quote_ident(column_name), ', ' order by ordinal_position),
         string_agg('m.' || quote_ident(column_name), ', ' order by ordinal_position)
    into v_cols, v_sel
  from information_schema.columns
  where table_schema = 'public' and table_name = 'communication_messages'
    and column_name not in ('id', 'account_id', 'thread_id');

  for r in select m.old_account_id, m.canonical_account_id, a.workspace_id as canon_ws
           from public.ops_r3_merge_map m
           join public.communication_accounts a on a.id = m.canonical_account_id
           where m.approved and m.canonical_account_id is not null
           order by m.old_account_id loop

    -- 1) hilos que faltan
    for v_id in
      insert into public.communication_threads
        (account_id, provider, external_thread_id, subject, participants, last_message_at, created_at, updated_at)
      select distinct on (t.external_thread_id) r.canonical_account_id, t.provider, t.external_thread_id,
             t.subject, t.participants, t.last_message_at, t.created_at, t.updated_at
      from public.communication_threads t
      where t.account_id = r.old_account_id
        and not exists (select 1 from public.communication_threads k
                        where k.account_id = r.canonical_account_id and k.external_thread_id = t.external_thread_id)
      order by t.external_thread_id, t.last_message_at desc nulls last
      on conflict (account_id, external_thread_id) do nothing
      returning id
    loop perform public.ops_r3_log(v_op, 'communication_threads', v_id, 'insert', null); end loop;

    -- 2) mensajes que faltan (hilo remapeado)
    for v_id in execute format($f$
        insert into public.communication_messages (account_id, thread_id, %1$s)
        select distinct on (m.external_message_id) $1,
               (select k.id from public.communication_threads k
                where k.account_id = $1 and k.external_thread_id = ot.external_thread_id), %2$s
        from public.communication_messages m
        left join public.communication_threads ot on ot.id = m.thread_id
        where m.account_id = $2
          and not exists (select 1 from public.communication_messages k
                          where k.account_id = $1 and k.external_message_id = m.external_message_id)
        order by m.external_message_id, m.created_at
        on conflict (account_id, external_message_id) do nothing
        returning id$f$, v_cols, v_sel)
      using r.canonical_account_id, r.old_account_id
    loop perform public.ops_r3_log(v_op, 'communication_messages', v_id, 'insert', null); end loop;

    -- 3) casos
    for c in select * from public.intelligent_cases where account_id = r.old_account_id order by created_at, id loop
      select coalesce(array_agg(distinct om.external_message_id order by om.external_message_id), '{}')
        into v_src_set
      from public.case_messages x join public.communication_messages om on om.id = x.message_id
      where x.case_id = c.id;
      select t.external_thread_id into v_src_thread from public.communication_threads t where t.id = c.primary_thread_id;

      -- ya migrado en una operación anterior: no repetir (idempotencia)
      select new_case_id into v_target from public.ops_r3_case_map where old_case_id = c.id limit 1;
      if v_target is not null then
        continue;
      end if;

      with cand as (
        select ic.id from public.intelligent_cases ic
        left join public.communication_threads kt on kt.id = ic.primary_thread_id
        where ic.account_id = r.canonical_account_id
          and (
            (c.metadata->>'event_key' is not null
             and ic.metadata->>'event_key' = c.metadata->>'event_key'
             and v_src_thread is not null and kt.external_thread_id = v_src_thread)
            or
            (cardinality(v_src_set) > 0 and v_src_set = (
               select coalesce(array_agg(distinct km.external_message_id order by km.external_message_id), '{}')
               from public.case_messages y join public.communication_messages km on km.id = y.message_id
               where y.case_id = ic.id))
          )
      )
      select count(*), min(id::text)::uuid into v_ncand, v_target from cand;

      if v_ncand = 1 then
        v_decision := 'fusionado';
      else
        v_decision := case when v_ncand = 0 then 'copiado' else 'copiado_ambiguo' end;
        v_new := gen_random_uuid();
        insert into public.intelligent_cases
        select (jsonb_populate_record(null::public.intelligent_cases,
                 to_jsonb(c) || jsonb_build_object(
                   'id', v_new, 'workspace_id', r.canon_ws, 'account_id', r.canonical_account_id,
                   'primary_thread_id', (select k.id from public.communication_threads k
                       where k.account_id = r.canonical_account_id and k.external_thread_id = v_src_thread),
                   'metadata', c.metadata || jsonb_build_object('r3_merged_from', c.id, 'r3_op', v_op)))).*;
        perform public.ops_r3_log(v_op, 'intelligent_cases', v_new, 'insert', null);
        v_target := v_new;
      end if;
      insert into public.ops_r3_case_map values (v_op, c.id, v_target, v_decision);

      -- 3a) eventos (dedupe: tipo, dedupe_key, título, fecha, mensaje)
      for e in select * from public.case_events where case_id = c.id order by created_at, id loop
        v_msg := (select k.id from public.communication_messages om
                  join public.communication_messages k
                    on k.account_id = r.canonical_account_id and k.external_message_id = om.external_message_id
                  where om.id = e.message_id);
        select x.id into v_ev from public.case_events x
        where x.case_id = v_target and x.event_type = e.event_type
          and coalesce(x.dedupe_key, '') = coalesce(e.dedupe_key, '') and x.title = e.title
          and x.created_at = e.created_at and x.message_id is not distinct from v_msg
        limit 1;
        if v_ev is null then
          insert into public.case_events (workspace_id, case_id, message_id, event_type, level, title,
                 description, actor_type, actor_identifier, dedupe_key, metadata, created_at)
          values (r.canon_ws, v_target, v_msg, e.event_type, e.level, e.title, e.description, e.actor_type,
                  e.actor_identifier, e.dedupe_key, e.metadata, e.created_at)
          returning id into v_ev;
          perform public.ops_r3_log(v_op, 'case_events', v_ev, 'insert', null);
        end if;
        insert into public.ops_r3_event_map values (v_op, e.id, v_ev) on conflict do nothing;
      end loop;

      -- 3b) participantes (dedupe por correo; los existentes no se modifican)
      for p in select * from public.case_participants where case_id = c.id order by first_seen_at, id loop
        if not exists (select 1 from public.case_participants x
                       where x.case_id = v_target and lower(x.email) = lower(p.email)) then
          insert into public.case_participants (case_id, email, display_name, participant_role, message_count,
                 first_seen_at, last_seen_at, metadata)
          values (v_target, p.email, p.display_name, p.participant_role, p.message_count,
                  p.first_seen_at, p.last_seen_at, p.metadata)
          returning id into v_id;
          perform public.ops_r3_log(v_op, 'case_participants', v_id, 'insert', null);
        end if;
      end loop;

      -- 3c) notificaciones (dedupe: canal, nivel, título, fecha)
      for n in select * from public.case_notifications where case_id = c.id order by created_at, id loop
        if not exists (select 1 from public.case_notifications x
                       where x.case_id = v_target and x.channel = n.channel and x.level = n.level
                         and x.title = n.title and x.created_at = n.created_at) then
          insert into public.case_notifications (workspace_id, case_id, event_id, level, channel, title, body,
                 delivered_at, read_at, metadata, created_at)
          values (r.canon_ws, v_target,
                  (select em.new_event_id from public.ops_r3_event_map em
                   where em.op_id = v_op and em.old_event_id = n.event_id),
                  n.level, n.channel, n.title, n.body, n.delivered_at, n.read_at,
                  n.metadata || jsonb_build_object('r3_merged_from', n.id), n.created_at)
          returning id into v_id;
          perform public.ops_r3_log(v_op, 'case_notifications', v_id, 'insert', null);
        end if;
      end loop;

      -- 3d) vínculos caso–mensaje (mensaje remapeado; message_id es único global)
      for v_id in
        insert into public.case_messages (case_id, message_id, relation_type, is_primary, sequence_number, linked_at)
        select v_target, k.id, x.relation_type, x.is_primary, x.sequence_number, x.linked_at
        from public.case_messages x
        join public.communication_messages om on om.id = x.message_id
        join public.communication_messages k
          on k.account_id = r.canonical_account_id and k.external_message_id = om.external_message_id
        where x.case_id = c.id
        on conflict do nothing
        returning id
      loop perform public.ops_r3_log(v_op, 'case_messages', v_id, 'insert', null); end loop;
    end loop;
  end loop;

  -- 4) retiro SOLO de filas aprobadas con canónica: credenciales a bitácora + superseded
  for r in select o.id, to_jsonb(o) as before_row from public.oauth_credentials o
           join public.ops_r3_merge_map m on m.old_account_id = o.account_id
           where m.approved and m.canonical_account_id is not null loop
    delete from public.oauth_credentials where id = r.id;
    perform public.ops_r3_log(v_op, 'oauth_credentials', r.id, 'delete', r.before_row);
  end loop;
  for r in select a.id, to_jsonb(a) as before_row from public.communication_accounts a
           join public.ops_r3_merge_map m on m.old_account_id = a.id
           where m.approved and m.canonical_account_id is not null and a.status <> 'superseded' loop
    update public.communication_accounts set status = 'superseded' where id = r.id;
    perform public.ops_r3_log(v_op, 'communication_accounts', r.id, 'update', r.before_row);
  end loop;

  update public.ops_r3_operation set status = 'done', finished_at = now() where op_id = v_op;
  raise notice 'op_id=%', v_op;
end $$;
commit;
