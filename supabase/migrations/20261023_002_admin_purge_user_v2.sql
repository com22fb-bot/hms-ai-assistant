-- admin_purge_user v2 — BORRADOR (PR #181). NO aplicar sin aprobación de ASTRA y Héctor.
--
-- POLÍTICA DE PROPIEDAD, DESCONEXIÓN Y CONSERVACIÓN (docs/ops/BORRADO_USUARIOS.md):
--  P1. Espacio de trabajo donde el usuario es el ÚNICO miembro activo: se borra completo
--      (buzones, hilos, mensajes, adjuntos, credenciales, trabajos, casos).
--  P2. Espacio compartido (hay otros miembros activos): NO se borran buzones ni mensajes.
--      - Los buzones que el usuario conectó se DESCONECTAN (status='disconnected'), se borran
--        SUS credenciales OAuth (no deben seguir leyendo el correo con su permiso) y se
--        REASIGNAN al dueño del espacio; si el dueño es el propio usuario, al miembro activo
--        más antiguo (que pasa a ser el nuevo dueño del espacio).
--      - Solo se quita su membresía y sus filas personales (reglas, avisos, preferencias).
--  P3. Buzón conectado por el usuario en un espacio del que no es miembro: igual que P2.
--  P4. Esquemas de respaldo: SOLO los que coinciden con ^hms_backup_[a-z0-9_]+$ (lista
--      explícita por patrón). Se borran únicamente las filas del usuario (por id de usuario,
--      buzón, mensaje o espacio borrado); nunca se borran esquemas ni tablas.
--  P5. Storage: las rutas de adjuntos se encolan en admin_storage_purge_queue DENTRO de la
--      misma transacción (duraderas). El backend las borra y reintenta con espera exponencial.
--  P6. p_dry_run = true: ejecuta todo en una subtransacción y la revierte; devuelve el plan
--      exacto (conteos por tabla y esquema, buzones conservados/reasignados) sin cambiar nada.

create table if not exists public.admin_storage_purge_queue (
  id bigserial primary key,
  bucket text not null,
  path text not null,
  status text not null default 'pendiente' check (status in ('pendiente', 'hecho', 'fallido')),
  attempts int not null default 0,
  max_attempts int not null default 8,
  next_attempt_at timestamptz not null default now(),
  last_error text,
  purge_ref uuid not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (bucket, path)
);
alter table public.admin_storage_purge_queue enable row level security;
revoke all on public.admin_storage_purge_queue from public, anon, authenticated;
grant select, insert, update on public.admin_storage_purge_queue to service_role;
grant usage on sequence public.admin_storage_purge_queue_id_seq to service_role;

drop function if exists public.admin_purge_user(uuid);
create or replace function public.admin_purge_user(p_user uuid, p_dry_run boolean default false)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_catalog
as $$
declare
  v_ref uuid := gen_random_uuid();
  v_plan jsonb;
  v_detail text;
begin
  if p_user is null then
    raise exception 'admin_purge_user: falta el usuario';
  end if;
  if exists (select 1 from public.admin_allowlist where user_id = p_user) then
    raise exception 'admin_purge_user: no se borra a un administrador';
  end if;
  if not p_dry_run then
    v_plan := public._admin_purge_user_exec(p_user, v_ref);
    insert into public.admin_events (source, severity, title, detail, status, created_by, meta)
    values ('manual', 'info', 'Usuario borrado desde /admin',
            format('Borrado: %s filas; %s archivos encolados; %s buzones compartidos conservados.',
                   v_plan->>'rows_total', v_plan->>'storage_queued', v_plan->>'shared_kept'),
            case when (v_plan->>'storage_queued')::int > 0 then 'abierto' else 'resuelto' end,
            'admin_purge_user',
            jsonb_build_object('kind', 'user_purge', 'purge_ref', v_ref) || (v_plan - 'storage_paths'));
    return v_plan || jsonb_build_object('dry_run', false, 'purge_ref', v_ref);
  end if;
  -- Simulación: misma lógica, revertida con una excepción controlada.
  begin
    v_plan := public._admin_purge_user_exec(p_user, v_ref);
    raise exception using errcode = 'P0001', message = 'dry_run_rollback', detail = v_plan::text;
  exception when sqlstate 'P0001' then
    if sqlerrm <> 'dry_run_rollback' then raise; end if;
    get stacked diagnostics v_detail = pg_exception_detail;
    v_plan := v_detail::jsonb;
  end;
  return (v_plan - 'storage_paths') || jsonb_build_object('dry_run', true);
end;
$$;

create or replace function public._admin_purge_user_exec(p_user uuid, p_ref uuid)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_catalog
as $$
declare
  v_ws uuid[];          -- espacios solo del usuario (P1)
  v_shared uuid[];      -- espacios compartidos (P2)
  v_acc uuid[];         -- buzones a borrar
  v_keep uuid[];        -- buzones a conservar/reasignar (P2/P3)
  v_msg uuid[];
  v_paths text[];
  v_counts jsonb := '{}'::jsonb;
  v_backup jsonb := '{}'::jsonb;
  v_reassigned jsonb := '[]'::jsonb;
  v_n bigint;
  v_total bigint := 0;
  v_heir uuid;
  r record;
  acc record;
begin
  -- Miembros "activos": status distinto de 'removed' y sin deleted_at.
  select coalesce(array_agg(x.id), '{}') into v_ws from (
    select w.id from public.workspaces w
    where (w.owner_profile_id = p_user
           or exists (select 1 from public.workspace_members m where m.workspace_id = w.id and m.profile_id = p_user))
      and not exists (select 1 from public.workspace_members m
                      where m.workspace_id = w.id and m.profile_id <> p_user
                        and coalesce(m.status, 'active') <> 'removed' and m.deleted_at is null)) x;

  select coalesce(array_agg(distinct m.workspace_id), '{}') into v_shared
  from public.workspace_members m
  where m.profile_id = p_user and m.workspace_id <> all(v_ws);

  select coalesce(array_agg(a.id), '{}') into v_acc
  from public.communication_accounts a where a.workspace_id = any(v_ws);

  select coalesce(array_agg(a.id), '{}') into v_keep
  from public.communication_accounts a
  where a.connected_by_profile_id = p_user and a.id <> all(v_acc);

  select coalesce(array_agg(m.id), '{}') into v_msg
  from public.communication_messages m where m.account_id = any(v_acc);

  -- P2/P3: reasignar y desconectar buzones compartidos (los mensajes se conservan).
  for acc in select a.id, a.workspace_id from public.communication_accounts a where a.id = any(v_keep) loop
    select coalesce(
      (select ws.owner_profile_id from public.workspaces ws
        where ws.id = acc.workspace_id and ws.owner_profile_id is distinct from p_user
          and exists (select 1 from public.workspace_members m where m.workspace_id = ws.id
                      and m.profile_id = ws.owner_profile_id and coalesce(m.status,'active') <> 'removed' and m.deleted_at is null)),
      (select m.profile_id from public.workspace_members m
        where m.workspace_id = acc.workspace_id and m.profile_id <> p_user
          and coalesce(m.status,'active') <> 'removed' and m.deleted_at is null
        order by coalesce(m.joined_at, m.created_at) nulls last, m.profile_id limit 1)) into v_heir;
    update public.communication_accounts
       set connected_by_profile_id = v_heir, status = 'disconnected', updated_at = now()
     where id = acc.id;
    v_reassigned := v_reassigned || jsonb_build_object('account_id', acc.id, 'to_profile', v_heir,
                                                       'kept_messages', (select count(*) from public.communication_messages where account_id = acc.id));
  end loop;
  delete from public.oauth_credentials where account_id = any(v_keep);
  get diagnostics v_n = row_count;
  if v_n > 0 then v_counts := v_counts || jsonb_build_object('oauth_credentials_shared', v_n); v_total := v_total + v_n; end if;

  -- Dueño de un espacio compartido: pasa al miembro activo más antiguo.
  for acc in select ws.id from public.workspaces ws where ws.owner_profile_id = p_user and ws.id = any(v_shared) loop
    update public.workspaces set owner_profile_id = (
      select m.profile_id from public.workspace_members m
       where m.workspace_id = acc.id and m.profile_id <> p_user
         and coalesce(m.status,'active') <> 'removed' and m.deleted_at is null
       order by coalesce(m.joined_at, m.created_at) nulls last, m.profile_id limit 1)
     where id = acc.id;
  end loop;

  -- P5: encolar rutas de Storage antes de borrar las filas de adjuntos.
  select coalesce(array_agg(distinct x.storage_path) filter (where nullif(x.storage_path, '') is not null), '{}') into v_paths
  from public.attachments x where x.message_id = any(v_msg);
  insert into public.admin_storage_purge_queue (bucket, path, purge_ref)
  select 'attachments', p, p_ref from unnest(v_paths) p
  on conflict (bucket, path) do update set status = 'pendiente', next_attempt_at = now(), updated_at = now();

  -- Hojas primero (public). Las tablas con account_id solo se borran para buzones borrados.
  for r in
    select c.table_name, c.column_name, k.ord
    from information_schema.columns c
    join information_schema.tables t
      on t.table_schema = c.table_schema and t.table_name = c.table_name and t.table_type = 'BASE TABLE'
    join (values ('message_id', 1), ('account_id', 2), ('workspace_id', 3), ('profile_id', 4), ('user_id', 5))
      as k(col, ord) on k.col = c.column_name
    where c.table_schema = 'public' and c.data_type = 'uuid'
      and c.table_name not in ('admin_events', 'admin_allowlist', 'admin_storage_purge_queue',
                               'communication_messages', 'communication_threads', 'communication_accounts',
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
  delete from public.workspace_members where profile_id = p_user or workspace_id = any(v_ws);
  get diagnostics v_n = row_count; v_counts := v_counts || jsonb_build_object('workspace_members', v_n); v_total := v_total + v_n;
  delete from public.workspaces where id = any(v_ws);
  get diagnostics v_n = row_count; v_counts := v_counts || jsonb_build_object('workspaces', v_n); v_total := v_total + v_n;

  -- P4: esquemas de respaldo por patrón explícito; solo filas del usuario.
  for r in
    select c.table_schema, c.table_name, c.column_name
    from information_schema.columns c
    join information_schema.tables t
      on t.table_schema = c.table_schema and t.table_name = c.table_name and t.table_type = 'BASE TABLE'
    where c.table_schema ~ '^hms_backup_[a-z0-9_]+$'
      and c.data_type = 'uuid'
      and (c.column_name in ('message_id', 'account_id', 'workspace_id', 'profile_id', 'user_id',
                             'connected_by_profile_id', 'owner_profile_id')
           or (c.column_name = 'id' and c.table_name in ('communication_messages', 'communication_accounts',
                                                          'workspaces', 'profiles', 'users')))
    order by 1, 2, 3
  loop
    if r.column_name = 'message_id' or (r.column_name = 'id' and r.table_name = 'communication_messages') then
      execute format('delete from %I.%I where %I = any($1)', r.table_schema, r.table_name, r.column_name) using v_msg;
    elsif r.column_name = 'account_id' or (r.column_name = 'id' and r.table_name = 'communication_accounts') then
      execute format('delete from %I.%I where %I = any($1)', r.table_schema, r.table_name, r.column_name) using v_acc;
    elsif r.column_name = 'workspace_id' or (r.column_name = 'id' and r.table_name = 'workspaces') then
      execute format('delete from %I.%I where %I = any($1)', r.table_schema, r.table_name, r.column_name) using v_ws;
    else  -- profile_id, user_id, connected_by_profile_id, owner_profile_id, profiles.id, users.id
      execute format('delete from %I.%I where %I = $1', r.table_schema, r.table_name, r.column_name) using p_user;
    end if;
    get diagnostics v_n = row_count;
    if v_n > 0 then
      v_backup := jsonb_set(v_backup, array[r.table_schema || '.' || r.table_name],
                            to_jsonb(coalesce((v_backup ->> (r.table_schema || '.' || r.table_name))::bigint, 0) + v_n));
      v_total := v_total + v_n;
    end if;
  end loop;

  delete from public.users where id = p_user;
  get diagnostics v_n = row_count; v_counts := v_counts || jsonb_build_object('users', v_n); v_total := v_total + v_n;
  delete from public.profiles where id = p_user;
  get diagnostics v_n = row_count; v_counts := v_counts || jsonb_build_object('profiles', v_n); v_total := v_total + v_n;
  delete from auth.users where id = p_user;
  get diagnostics v_n = row_count; v_counts := v_counts || jsonb_build_object('auth_users', v_n);

  return jsonb_build_object(
    'rows_total', v_total, 'counts', v_counts, 'backup_counts', v_backup,
    'workspaces_deleted', coalesce(array_length(v_ws, 1), 0),
    'workspaces_shared', coalesce(array_length(v_shared, 1), 0),
    'shared_kept', jsonb_array_length(v_reassigned), 'shared_accounts', v_reassigned,
    'storage_queued', coalesce(array_length(v_paths, 1), 0), 'storage_paths', to_jsonb(v_paths));
end;
$$;

-- Cola de Storage: reclamar y marcar (el backend no toca la tabla directamente).
create or replace function public.admin_storage_purge_claim(p_limit int default 100)
returns table(id bigint, bucket text, path text, attempts int)
language sql security definer set search_path = public, pg_catalog as $$
  update public.admin_storage_purge_queue q
     set attempts = q.attempts + 1, updated_at = now(),
         next_attempt_at = now() + make_interval(secs => least(3600, 30 * power(2, q.attempts)::int))
   where q.id in (select id from public.admin_storage_purge_queue
                   where status = 'pendiente' and next_attempt_at <= now()
                   order by id limit greatest(1, least(p_limit, 500)) for update skip locked)
  returning q.id, q.bucket, q.path, q.attempts
$$;

create or replace function public.admin_storage_purge_mark(p_ids bigint[], p_ok boolean, p_error text default null)
returns jsonb
language plpgsql security definer set search_path = public, pg_catalog as $$
declare v_done int; v_failed int; v_pending int;
begin
  if p_ok then
    update public.admin_storage_purge_queue set status = 'hecho', last_error = null, updated_at = now() where id = any(p_ids);
  else
    update public.admin_storage_purge_queue
       set status = case when attempts >= max_attempts then 'fallido' else 'pendiente' end,
           last_error = left(coalesce(p_error, 'error'), 200), updated_at = now()
     where id = any(p_ids);
  end if;
  select count(*) filter (where status = 'hecho'), count(*) filter (where status = 'fallido'),
         count(*) filter (where status = 'pendiente')
    into v_done, v_failed, v_pending from public.admin_storage_purge_queue where id = any(p_ids);
  return jsonb_build_object('hecho', v_done, 'fallido', v_failed, 'pendiente', v_pending);
end;
$$;

create or replace function public.admin_storage_purge_status()
returns jsonb language sql security definer set search_path = public, pg_catalog as $$
  select jsonb_build_object(
    'pendiente', count(*) filter (where status = 'pendiente'),
    'fallido', count(*) filter (where status = 'fallido'),
    'hecho', count(*) filter (where status = 'hecho'),
    'mas_antiguo_pendiente', min(created_at) filter (where status = 'pendiente'))
  from public.admin_storage_purge_queue
$$;

revoke all on function public.admin_purge_user(uuid, boolean) from public, anon, authenticated;
revoke all on function public._admin_purge_user_exec(uuid, uuid) from public, anon, authenticated, service_role;
revoke all on function public.admin_storage_purge_claim(int) from public, anon, authenticated;
revoke all on function public.admin_storage_purge_mark(bigint[], boolean, text) from public, anon, authenticated;
revoke all on function public.admin_storage_purge_status() from public, anon, authenticated;
grant execute on function public.admin_purge_user(uuid, boolean) to service_role;
grant execute on function public.admin_storage_purge_claim(int) to service_role;
grant execute on function public.admin_storage_purge_mark(bigint[], boolean, text) to service_role;
grant execute on function public.admin_storage_purge_status() to service_role;
-- La firma anterior (uuid) se reemplaza: PostgREST resuelve {"p_user"} a la nueva por el valor por defecto.
-- Un solo buzón vivo por dirección, sin importar el proveedor.
create unique index if not exists ux_comm_accounts_live_address_any
  on public.communication_accounts (address_key)
  where status in ('active', 'needs_reauth');

-- Bitácora por buzón (solo lectura, sin contenido de correos).
create or replace function public.admin_mailbox_timeline(p_account uuid)
returns table(at timestamptz, kind text, detail text)
language sql security definer set search_path = public, pg_catalog as $$
  select a.created_at, 'conexion', a.provider || ' conectado' from communication_accounts a where a.id = p_account
  union all select o.updated_at, 'token', 'credencial actualizada' from oauth_credentials o where o.account_id = p_account
  union all select j.started_at, 'sync_inicio', j.mode || ' · ' || j.status from gmail_sync_jobs j where j.account_id = p_account and j.started_at is not null
  union all select j.completed_at, 'sync_fin', format('%s nuevos · %s duplicados · %s errores', j.messages_inserted, j.duplicates, j.errors) from gmail_sync_jobs j where j.account_id = p_account and j.completed_at is not null
  union all select date_trunc('hour', m.created_at), 'descarga', count(*) || ' correos guardados' from communication_messages m where m.account_id = p_account group by 1
  union all select date_trunc('hour', m.processed_at), 'proceso', count(*) || ' correos procesados' from communication_messages m where m.account_id = p_account and m.processed_at is not null group by 1
  union all select a.last_sync_at, 'ultima_sync', 'última sincronización' from communication_accounts a where a.id = p_account and a.last_sync_at is not null
  order by 1 desc nulls last
$$;
revoke all on function public.admin_mailbox_timeline(uuid) from public, anon, authenticated;
grant execute on function public.admin_mailbox_timeline(uuid) to service_role;
