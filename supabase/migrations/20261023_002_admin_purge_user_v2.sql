-- admin_purge_user v2 (NO aplicada; requiere confirmación de Héctor).
-- Corrige: (1) buzones conectados por el usuario en espacios compartidos quedaban vivos
-- (connected_by_profile_id ON DELETE SET NULL); (2) archivos de adjuntos en Storage no se borraban;
-- (3) regla "un buzón por dirección": índice único por address_key entre proveedores (google vs gmail_imap).
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
  v_paths text[];
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
  where a.workspace_id = any(v_ws)
     or a.connected_by_profile_id = p_user;  -- buzones que conectó en espacios compartidos

  select coalesce(array_agg(m.id), '{}') into v_msg
  from public.communication_messages m
  where m.account_id = any(v_acc);

  -- Rutas de Storage de los adjuntos: se devuelven para que el backend las borre
  -- (Storage no se borra desde SQL de forma soportada).
  select coalesce(array_agg(x.storage_path) filter (where x.storage_path is not null), '{}') into v_paths
  from public.attachments x where x.message_id = any(v_msg);

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

  return jsonb_build_object('rows_total', v_total, 'counts', v_counts, 'storage_paths', to_jsonb(v_paths));
end;
$$;

-- Un solo buzón vivo por dirección, sin importar el proveedor (antes era por (provider, address_key)).
-- Requiere que no existan dos filas vivas con la misma address_key (hoy: 1 viva para hmcelinfo).
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
