-- 20261031_001_conc01_commit_message — CONC-01 R2 (PR #214)
-- NO APLICAR en producción sin dictamen favorable de ASTRA y conformidad de Héctor.
-- No destructiva: solo crea UNA función y sus permisos. No toca tablas, índices ni datos.
-- Rollback: supabase/rollbacks/20261031_001_conc01_commit_message_rollback.sql
--
-- public.conc01_commit_message(p_message_id, p_workspace_id, p_account_id, p_token, p_ops)
-- Aplica en UNA transacción todas las escrituras de negocio de un mensaje reclamado:
--   1) SELECT ... FOR UPDATE de la fila de public.communication_messages (por PK);
--   2) valida id + cuenta + workspace (vía public.communication_accounts) + testigo
--      vigente (triage_reason = p_token, 'classifying:<uuid>') + case_processed = false;
--   3) ejecuta las operaciones preparadas por el trabajador (casos, eventos, notificaciones,
--      vínculos, participantes, patrones de aprendizaje, estado final y triage) validando
--      que cada fila pertenece al mismo workspace/cuenta/mensaje.
-- Validación fallida -> {"status":"claim_lost"} y 0 escrituras.
-- Cualquier error en una escritura -> excepción -> rollback completo de la transacción.
-- SECURITY INVOKER: corre con los permisos y la RLS del rol que llama (service_role en el
-- backend). No concede privilegios adicionales.
create or replace function public.conc01_commit_message(
  p_message_id uuid,
  p_workspace_id uuid,
  p_account_id uuid,
  p_token text,
  p_ops jsonb
) returns jsonb
language plpgsql
security invoker
set search_path = pg_catalog, pg_temp
as $$
declare
  v_account uuid;
  v_processed boolean;
  v_reason text;
  v_ws uuid;
  op jsonb;
  v_table text;
  v_kind text;
  v_row jsonb;
  v_where jsonb;
  v_cols text;
  v_sets text;
  v_cond text;
  v_extra text;
  v_applied int := 0;
  v_skipped int := 0;
  v_n int;
begin
  -- Parámetros: tipos los valida la firma; valores aquí.
  if p_message_id is null or p_workspace_id is null or p_account_id is null then
    raise exception 'conc01: parámetros incompletos' using errcode = '22023';
  end if;
  if p_token is null or p_token !~ '^classifying:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' then
    raise exception 'conc01: testigo inválido' using errcode = '22023';
  end if;
  if p_ops is null or jsonb_typeof(p_ops) <> 'array' or jsonb_array_length(p_ops) > 200 then
    raise exception 'conc01: operaciones inválidas' using errcode = '22023';
  end if;

  -- Único bloqueo explícito, siempre primero y por PK (orden de bloqueo constante).
  select m.account_id, m.case_processed, m.triage_reason
    into v_account, v_processed, v_reason
    from public.communication_messages m
   where m.id = p_message_id
   for update;

  if not found or v_account is distinct from p_account_id or v_processed
     or v_reason is distinct from p_token then
    return jsonb_build_object('status', 'claim_lost');
  end if;

  select a.workspace_id into v_ws from public.communication_accounts a where a.id = p_account_id;
  if v_ws is distinct from p_workspace_id then
    return jsonb_build_object('status', 'claim_lost');
  end if;

  for op in select value from jsonb_array_elements(p_ops) loop
    v_table := op->>'table';
    v_kind := op->>'kind';
    v_row := op->'row';
    v_where := op->'where';
    v_extra := '';

    if v_table is null or v_table not in ('intelligent_cases', 'case_events', 'case_notifications',
        'case_messages', 'case_participants', 'organizational_patterns', 'communication_messages') then
      raise exception 'conc01: tabla no permitida' using errcode = '22023';
    end if;

    if v_kind = 'insert' then
      if jsonb_typeof(v_row) <> 'object' then
        raise exception 'conc01: fila inválida' using errcode = '22023';
      end if;
      -- Aislamiento: cada fila nueva pertenece al mismo workspace / cuenta / mensaje.
      if v_table in ('intelligent_cases', 'case_events', 'case_notifications', 'organizational_patterns')
         and (v_row->>'workspace_id')::uuid is distinct from p_workspace_id then
        raise exception 'conc01: workspace no coincide' using errcode = '42501';
      end if;
      if v_table = 'intelligent_cases' and (v_row->>'account_id')::uuid is distinct from p_account_id then
        raise exception 'conc01: cuenta no coincide' using errcode = '42501';
      end if;
      if v_table in ('case_messages', 'case_events') and v_row ? 'message_id'
         and (v_row->>'message_id')::uuid is distinct from p_message_id then
        raise exception 'conc01: mensaje no coincide' using errcode = '42501';
      end if;
      if v_table in ('case_messages', 'case_participants', 'case_events', 'case_notifications')
         and not exists (select 1 from public.intelligent_cases c
                          where c.id = (v_row->>'case_id')::uuid and c.workspace_id = p_workspace_id) then
        raise exception 'conc01: caso de otro workspace' using errcode = '42501';
      end if;
      if v_table = 'communication_messages' then
        raise exception 'conc01: insert de mensaje no permitido' using errcode = '42501';
      end if;
      -- Notificación de un evento omitido por dedupe: tampoco se escribe.
      if op ? 'requires_event'
         and not exists (select 1 from public.case_events e where e.id = (op->>'requires_event')::uuid) then
        v_skipped := v_skipped + 1;
        continue;
      end if;
      select string_agg(format('%I', k), ', ') into v_cols from jsonb_object_keys(v_row) as k;
      execute format(
        'insert into public.%I (%s) select %s from jsonb_populate_record(null::public.%I, $1) %s',
        v_table, v_cols, v_cols, v_table,
        case when op->>'on_conflict' = 'nothing' and v_table = 'case_events' then 'on conflict do nothing' else '' end
      ) using v_row;

    elsif v_kind = 'update' then
      if jsonb_typeof(v_where) <> 'object' or not (v_where ? 'id') or jsonb_typeof(op->'set') <> 'object' then
        raise exception 'conc01: update sin filtro por id' using errcode = '22023';
      end if;
      -- Aislamiento de filas existentes.
      if v_table = 'communication_messages' then
        if (v_where->>'id')::uuid is distinct from p_message_id then
          raise exception 'conc01: update de otro mensaje' using errcode = '42501';
        end if;
      elsif v_table in ('intelligent_cases', 'organizational_patterns') then
        v_extra := format(' and t.workspace_id = %L::uuid', p_workspace_id);
      elsif v_table = 'case_participants' then
        v_extra := format(' and exists (select 1 from public.intelligent_cases c where c.id = t.case_id and c.workspace_id = %L::uuid)', p_workspace_id);
      else
        raise exception 'conc01: update no permitido' using errcode = '42501';
      end if;
      if (op->'set') ?| array['id', 'workspace_id', 'account_id'] then
        raise exception 'conc01: columnas de identidad inmutables' using errcode = '42501';
      end if;
      select string_agg(format('%I = r.%I', k, k), ', ') into v_sets from jsonb_object_keys(op->'set') as k;
      -- id con '=' para usar la PK (IS NOT DISTINCT FROM no usa índice); el resto, null-seguro.
      select string_agg(case when k = 'id' then 't.id = w.id'
                             else format('t.%I is not distinct from w.%I', k, k) end, ' and ') into v_cond
        from jsonb_object_keys(v_where) as k;
      execute format(
        'update public.%I t set %s from jsonb_populate_record(null::public.%I, $1) r, '
        'jsonb_populate_record(null::public.%I, $2) w where %s%s',
        v_table, v_sets, v_table, v_table, v_cond, v_extra
      ) using op->'set', v_where;
    else
      raise exception 'conc01: operación no permitida' using errcode = '22023';
    end if;
    get diagnostics v_n = row_count;
    v_applied := v_applied + v_n;
  end loop;

  return jsonb_build_object('status', 'ok', 'applied', v_applied, 'skipped', v_skipped);
end;
$$;

comment on function public.conc01_commit_message(uuid, uuid, uuid, text, jsonb) is
  'CONC-01 R2: escrituras atómicas de un mensaje reclamado (FOR UPDATE + testigo). PR #214.';

revoke all on function public.conc01_commit_message(uuid, uuid, uuid, text, jsonb) from public;
do $$
begin
  if exists (select 1 from pg_catalog.pg_roles where rolname = 'anon') then
    revoke all on function public.conc01_commit_message(uuid, uuid, uuid, text, jsonb) from anon;
  end if;
  if exists (select 1 from pg_catalog.pg_roles where rolname = 'authenticated') then
    revoke all on function public.conc01_commit_message(uuid, uuid, uuid, text, jsonb) from authenticated;
  end if;
  if exists (select 1 from pg_catalog.pg_roles where rolname = 'service_role') then
    grant execute on function public.conc01_commit_message(uuid, uuid, uuid, text, jsonb) to service_role;
  end if;
end $$;
