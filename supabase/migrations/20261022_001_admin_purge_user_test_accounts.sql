-- 1) Borrado completo y transaccional de un usuario desde /admin.
-- 2) Cuentas de prueba: account_plans.is_test (true por defecto) y alta
--    automática del plan de prueba (3 días) para cada usuario nuevo.
-- Fase de pruebas: el borrado NO respalda datos. La bitácora solo guarda
-- conteos por tabla (sin correo, nombre ni ID del usuario).

alter table public.account_plans
  add column if not exists is_test boolean not null default true,
  add column if not exists trial_started_at timestamptz;

create or replace function public.admin_purge_user(p_user uuid)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_catalog
as $$
declare
  v_ws uuid[];
  v_acc uuid[];
  v_msg uuid[];
  v_counts jsonb := '{}'::jsonb;
  v_n bigint;
  v_total bigint := 0;
  r record;
begin
  if p_user is null then
    raise exception 'admin_purge_user: falta el usuario';
  end if;
  if exists (select 1 from public.admin_allowlist where user_id = p_user) then
    raise exception 'admin_purge_user: no se borra a un administrador';
  end if;

  -- Espacios de trabajo donde el usuario es el único miembro (o dueño sin otros).
  select coalesce(array_agg(w.id), '{}') into v_ws
  from public.workspaces w
  where (w.owner_profile_id = p_user
         or exists (select 1 from public.workspace_members m where m.workspace_id = w.id and m.profile_id = p_user))
    and not exists (select 1 from public.workspace_members m
                    where m.workspace_id = w.id and m.profile_id <> p_user);

  select coalesce(array_agg(a.id), '{}') into v_acc
  from public.communication_accounts a
  where a.workspace_id = any(v_ws);

  select coalesce(array_agg(m.id), '{}') into v_msg
  from public.communication_messages m
  where m.account_id = any(v_acc);

  -- Hojas primero, luego padres; se cuenta cada tabla (las cascadas restantes
  -- quedan en "cascade_only").
  for r in
    select c.table_name, c.column_name, k.ord
    from information_schema.columns c
    join information_schema.tables t
      on t.table_schema = c.table_schema and t.table_name = c.table_name and t.table_type = 'BASE TABLE'
    join (values ('message_id', 1), ('account_id', 2), ('workspace_id', 3), ('profile_id', 4), ('user_id', 5))
      as k(col, ord) on k.col = c.column_name
    where c.table_schema = 'public'
      and c.data_type = 'uuid'
      and c.table_name not in ('admin_events', 'admin_allowlist', 'communication_messages',
                               'communication_threads', 'communication_accounts',
                               'workspaces', 'workspace_members', 'profiles', 'users')
      and c.table_name not like 'ops\_%'
    order by k.ord, c.table_name
  loop
    if r.column_name = 'message_id' then
      execute format('delete from public.%I where message_id = any($1)', r.table_name) using v_msg;
    elsif r.column_name = 'account_id' then
      execute format('delete from public.%I where account_id = any($1)', r.table_name) using v_acc;
    elsif r.column_name = 'workspace_id' then
      execute format('delete from public.%I where workspace_id = any($1)', r.table_name) using v_ws;
    else
      execute format('delete from public.%I where %I = $1', r.table_name, r.column_name) using p_user;
    end if;
    get diagnostics v_n = row_count;
    if v_n > 0 then
      v_counts := jsonb_set(v_counts, array[r.table_name],
                            to_jsonb(coalesce((v_counts ->> r.table_name)::bigint, 0) + v_n));
      v_total := v_total + v_n;
    end if;
  end loop;

  delete from public.communication_messages where id = any(v_msg);
  get diagnostics v_n = row_count; v_counts := v_counts || jsonb_build_object('communication_messages', v_n); v_total := v_total + v_n;
  delete from public.communication_threads where account_id = any(v_acc);
  get diagnostics v_n = row_count; v_counts := v_counts || jsonb_build_object('communication_threads', v_n); v_total := v_total + v_n;
  delete from public.communication_accounts where id = any(v_acc);
  get diagnostics v_n = row_count; v_counts := v_counts || jsonb_build_object('communication_accounts', v_n); v_total := v_total + v_n;
  -- Membresías en espacios compartidos: solo se quita al usuario.
  delete from public.workspace_members where profile_id = p_user or workspace_id = any(v_ws);
  get diagnostics v_n = row_count; v_counts := v_counts || jsonb_build_object('workspace_members', v_n); v_total := v_total + v_n;
  delete from public.workspaces where id = any(v_ws);
  get diagnostics v_n = row_count; v_counts := v_counts || jsonb_build_object('workspaces', v_n); v_total := v_total + v_n;
  delete from public.users where id = p_user;
  get diagnostics v_n = row_count; v_counts := v_counts || jsonb_build_object('users', v_n); v_total := v_total + v_n;
  delete from public.profiles where id = p_user;
  get diagnostics v_n = row_count; v_counts := v_counts || jsonb_build_object('profiles', v_n); v_total := v_total + v_n;
  delete from auth.users where id = p_user;
  get diagnostics v_n = row_count; v_counts := v_counts || jsonb_build_object('auth_users', v_n);

  insert into public.admin_events (source, severity, title, detail, status, created_by, meta)
  values ('manual', 'info', 'Usuario borrado desde /admin',
          format('Borrado completo sin respaldo (fase de pruebas): %s filas.', v_total),
          'resuelto', 'admin_purge_user',
          jsonb_build_object('kind', 'user_purge', 'rows_total', v_total, 'counts', v_counts,
                             'workspaces', coalesce(array_length(v_ws, 1), 0)));

  return jsonb_build_object('rows_total', v_total, 'counts', v_counts);
end;
$$;
revoke all on function public.admin_purge_user(uuid) from public, anon, authenticated;
grant execute on function public.admin_purge_user(uuid) to service_role;

-- Alta automática: toda cuenta nueva es de prueba (3 días).
create or replace function public.donexto_new_user_plan()
returns trigger
language plpgsql
security definer
set search_path = public, pg_catalog
as $$
begin
  insert into public.account_plans (user_id, plan_code, status, trial_started_at, trial_ends_at, is_test)
  values (new.id, 'trial', 'trialing', now(), now() + interval '3 days', true)
  on conflict (user_id) do nothing;
  return new;
exception when others then
  return new; -- nunca bloquear el registro
end;
$$;
revoke all on function public.donexto_new_user_plan() from public, anon, authenticated;

drop trigger if exists trg_donexto_new_user_plan on auth.users;
create trigger trg_donexto_new_user_plan
  after insert on auth.users
  for each row execute function public.donexto_new_user_plan();
