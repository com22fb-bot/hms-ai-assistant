-- RONDA 3 · PREPARADA · NO APLICAR SIN APROBACIÓN
-- Fase A2: solo actúa sobre filas approved = true del mapa.
-- 1) copia a la canónica hilos/mensajes/casos que solo existen en copias
-- 2) respalda y quita credenciales de las copias y las marca 'superseded'.
-- No borra mensajes, hilos ni casos de las copias (purga diferida, otra aprobación).
begin;
create table if not exists public.ops_r3_inserted (
  table_name text not null, row_id uuid not null, primary key (table_name, row_id));
create table if not exists public.ops_r3_case_map (
  old_case_id uuid primary key, new_case_id uuid not null, created boolean not null);

do $$
declare
  r record; c record; v_key text; v_target uuid; v_new uuid; v_ws uuid; v_cols text;
begin
  if exists (select 1 from public.message_classification_rules x
             join public.ops_r3_merge_map m on m.old_account_id = x.account_id and m.approved)
     or exists (select 1 from public.message_watch_rules x
             join public.ops_r3_merge_map m on m.old_account_id = x.account_id and m.approved) then
    raise exception 'Hay reglas en cuentas a retirar: revisión manual requerida';
  end if;

  -- columnas de mensajes salvo id/account_id/thread_id (robusto ante columnas nuevas)
  select string_agg(quote_ident(column_name), ', ' order by ordinal_position) into v_cols
  from information_schema.columns
  where table_schema = 'public' and table_name = 'communication_messages'
    and column_name not in ('id', 'account_id', 'thread_id');

  for r in select m.old_account_id, m.canonical_account_id, a.workspace_id as canon_ws
           from public.ops_r3_merge_map m
           join public.communication_accounts a on a.id = m.canonical_account_id
           where m.approved and m.canonical_account_id is not null
           order by m.old_account_id loop
    -- hilos que faltan
    with ins as (
      insert into public.communication_threads
        (account_id, provider, external_thread_id, subject, participants, last_message_at, created_at, updated_at)
      select distinct on (t.external_thread_id) r.canonical_account_id, t.provider, t.external_thread_id,
             t.subject, t.participants, t.last_message_at, t.created_at, now()
      from public.communication_threads t
      where t.account_id = r.old_account_id
        and not exists (select 1 from public.communication_threads k
                        where k.account_id = r.canonical_account_id
                          and k.external_thread_id = t.external_thread_id)
      order by t.external_thread_id, t.last_message_at desc nulls last
      on conflict (account_id, external_thread_id) do nothing
      returning id)
    insert into public.ops_r3_inserted select 'communication_threads', id from ins;

    -- mensajes que faltan (hilo remapeado por external_thread_id)
    execute format($f$
      with ins as (
        insert into public.communication_messages (account_id, thread_id, %1$s)
        select distinct on (m.external_message_id) $1,
               (select k.id from public.communication_threads k
                where k.account_id = $1 and k.external_thread_id = ot.external_thread_id),
               %2$s
        from public.communication_messages m
        left join public.communication_threads ot on ot.id = m.thread_id
        where m.account_id = $2
          and not exists (select 1 from public.communication_messages k
                          where k.account_id = $1 and k.external_message_id = m.external_message_id)
        order by m.external_message_id, m.created_at
        on conflict (account_id, external_message_id) do nothing
        returning id)
      insert into public.ops_r3_inserted select 'communication_messages', id from ins$f$,
      v_cols, (select string_agg('m.' || x, ', ') from unnest(string_to_array(v_cols, ', ')) x))
    using r.canonical_account_id, r.old_account_id;

    -- casos
    for c in select * from public.intelligent_cases where account_id = r.old_account_id loop
      v_key := coalesce(c.metadata->>'event_key', c.normalized_subject, c.title);
      select ic.id into v_target from public.intelligent_cases ic
      where ic.account_id = r.canonical_account_id
        and coalesce(ic.metadata->>'event_key', ic.normalized_subject, ic.title) = v_key
      order by ic.created_at limit 1;
      if v_target is not null then
        insert into public.ops_r3_case_map values (c.id, v_target, false) on conflict do nothing;
      else
        v_new := gen_random_uuid();
        insert into public.intelligent_cases
        select (jsonb_populate_record(null::public.intelligent_cases,
                 to_jsonb(c) || jsonb_build_object(
                   'id', v_new, 'workspace_id', r.canon_ws, 'account_id', r.canonical_account_id,
                   'primary_thread_id', (select k.id from public.communication_threads k
                       join public.communication_threads ot on ot.id = c.primary_thread_id
                       where k.account_id = r.canonical_account_id
                         and k.external_thread_id = ot.external_thread_id),
                   'metadata', c.metadata || jsonb_build_object('r3_merged_from', c.id)))).*;
        insert into public.ops_r3_inserted values ('intelligent_cases', v_new);
        insert into public.ops_r3_case_map values (c.id, v_new, true);
        v_target := v_new;

        with ins as (
          insert into public.case_events (workspace_id, case_id, message_id, event_type, level, title,
                 description, actor_type, actor_identifier, dedupe_key, metadata, created_at)
          select r.canon_ws, v_new,
                 (select k.id from public.communication_messages k join public.communication_messages om
                    on om.id = e.message_id
                  where k.account_id = r.canonical_account_id and k.external_message_id = om.external_message_id),
                 e.event_type, e.level, e.title, e.description, e.actor_type, e.actor_identifier,
                 e.dedupe_key, e.metadata, e.created_at
          from public.case_events e where e.case_id = c.id
          returning id)
        insert into public.ops_r3_inserted select 'case_events', id from ins;

        with ins as (
          insert into public.case_participants (case_id, email, display_name, participant_role,
                 message_count, first_seen_at, last_seen_at, metadata)
          select v_new, p.email, p.display_name, p.participant_role, p.message_count,
                 p.first_seen_at, p.last_seen_at, p.metadata
          from public.case_participants p where p.case_id = c.id
          returning id)
        insert into public.ops_r3_inserted select 'case_participants', id from ins;
      end if;

      -- vínculos caso-mensaje (mensaje remapeado a la canónica)
      with ins as (
        insert into public.case_messages (case_id, message_id, relation_type, is_primary, sequence_number, linked_at)
        select v_target, k.id, cm.relation_type, cm.is_primary, cm.sequence_number, cm.linked_at
        from public.case_messages cm
        join public.communication_messages om on om.id = cm.message_id
        join public.communication_messages k
          on k.account_id = r.canonical_account_id and k.external_message_id = om.external_message_id
        where cm.case_id = c.id
        on conflict do nothing
        returning id)
      insert into public.ops_r3_inserted select 'case_messages', id from ins;
      v_target := null;
    end loop;
  end loop;
end $$;

-- respaldo y retiro de credenciales + estado
create table if not exists public.ops_r3_oauth_backup as
select o.* from public.oauth_credentials o where false;
insert into public.ops_r3_oauth_backup
select o.* from public.oauth_credentials o
join public.ops_r3_merge_map m on m.old_account_id = o.account_id and m.approved;
delete from public.oauth_credentials o
using public.ops_r3_merge_map m where m.old_account_id = o.account_id and m.approved;
update public.communication_accounts a set status = 'superseded', updated_at = now()
from public.ops_r3_merge_map m where m.old_account_id = a.id and m.approved;
commit;
