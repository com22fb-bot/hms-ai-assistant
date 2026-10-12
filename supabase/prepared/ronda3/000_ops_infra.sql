-- RONDA 3 · PREPARADA · NO APLICAR SIN APROBACIÓN
-- Infraestructura de operaciones: id de operación, bitácora fila a fila con hash,
-- respaldo, reporte de rollback y función de rollback que NO pisa actividad posterior.
begin;
create table if not exists public.ops_r3_operation (
  op_id uuid primary key default gen_random_uuid(),
  script text not null,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  status text not null default 'running'
);
create table if not exists public.ops_r3_rows (
  seq bigserial primary key,
  op_id uuid not null references public.ops_r3_operation(op_id),
  table_name text not null,
  row_id uuid not null,
  action text not null check (action in ('insert', 'update', 'delete')),
  before_row jsonb,          -- fila previa (update/delete); para credenciales queda solo aquí
  after_hash text            -- md5 de la fila tras la operación (insert/update)
);
create index if not exists ops_r3_rows_op on public.ops_r3_rows (op_id, seq);
create table if not exists public.ops_r3_rollback_report (
  op_id uuid not null,
  table_name text not null,
  row_id uuid not null,
  outcome text not null,     -- reverted | skipped_changed | skipped_dependents | skipped_conflict | already_gone
  detail text,
  at timestamptz not null default now()
);
-- Tablas internas: sin acceso desde la API (RLS sin políticas + sin grants).
alter table public.ops_r3_operation enable row level security;
alter table public.ops_r3_rows enable row level security;
alter table public.ops_r3_rollback_report enable row level security;
do $$ begin
  if exists (select 1 from pg_roles where rolname = 'anon') then
    revoke all on public.ops_r3_operation, public.ops_r3_rows, public.ops_r3_rollback_report from anon, authenticated;
  end if;
end $$;

create or replace function public.ops_r3_row_hash(p_table text, p_id uuid)
returns text language plpgsql stable set search_path = public as $$
declare h text;
begin
  execute format('select md5(to_jsonb(t)::text) from public.%I t where t.id = $1', p_table)
    into h using p_id;
  return h;
end $$;

create or replace function public.ops_r3_log(p_op uuid, p_table text, p_id uuid, p_action text, p_before jsonb)
returns void language plpgsql set search_path = public as $$
begin
  insert into public.ops_r3_rows (op_id, table_name, row_id, action, before_row, after_hash)
  values (p_op, p_table, p_id, p_action, p_before,
          case when p_action = 'delete' then null else public.ops_r3_row_hash(p_table, p_id) end);
end $$;

-- ¿Tiene la fila hijos (por cualquier FK) que no pertenezcan a la operación?
create or replace function public.ops_r3_has_children(p_table text, p_id uuid)
returns boolean language plpgsql stable set search_path = public as $$
declare fk record; found boolean;
begin
  for fk in
    select c.conrelid::regclass::text as child, a.attname as col
    from pg_constraint c
    join pg_attribute a on a.attrelid = c.conrelid and a.attnum = c.conkey[1]
    where c.contype = 'f' and c.confrelid = ('public.' || p_table)::regclass
      and array_length(c.conkey, 1) = 1
  loop
    execute format('select exists (select 1 from %s where %I = $1)', fk.child, fk.col) into found using p_id;
    if found then return true; end if;
  end loop;
  return false;
end $$;

-- Rollback seguro de una operación: recorre la bitácora en orden inverso.
create or replace function public.ops_r3_rollback(p_op uuid)
returns table (outcome text, n bigint)
language plpgsql set search_path = public as $$
declare r record; cur text; cols text;
begin
  -- restaurar valores exactos (incluido updated_at) sin que el trigger los pise
  alter table public.communication_accounts disable trigger user;
  alter table public.oauth_credentials disable trigger user;
  alter table public.communication_messages disable trigger user;
  for r in select * from public.ops_r3_rows where op_id = p_op order by seq desc loop
    if r.action = 'insert' then
      cur := public.ops_r3_row_hash(r.table_name, r.row_id);
      if cur is null then
        insert into public.ops_r3_rollback_report values (p_op, r.table_name, r.row_id, 'already_gone', null);
      elsif cur <> r.after_hash then
        insert into public.ops_r3_rollback_report values (p_op, r.table_name, r.row_id, 'skipped_changed',
          'la fila cambió después de la operación');
      elsif public.ops_r3_has_children(r.table_name, r.row_id) then
        insert into public.ops_r3_rollback_report values (p_op, r.table_name, r.row_id, 'skipped_dependents',
          'tiene filas hijas posteriores');
      else
        execute format('delete from public.%I where id = $1', r.table_name) using r.row_id;
        insert into public.ops_r3_rollback_report values (p_op, r.table_name, r.row_id, 'reverted', null);
      end if;
    elsif r.action = 'update' then
      cur := public.ops_r3_row_hash(r.table_name, r.row_id);
      if cur is distinct from r.after_hash then
        insert into public.ops_r3_rollback_report values (p_op, r.table_name, r.row_id, 'skipped_changed',
          'actividad posterior: no se restaura');
      else
        select string_agg(format('%I = src.%I', column_name, column_name), ', ') into cols
        from information_schema.columns
        where table_schema = 'public' and table_name = r.table_name and column_name <> 'id';
        execute format('update public.%I t set %s from jsonb_populate_record(null::public.%I, $1) src where t.id = $2',
                       r.table_name, cols, r.table_name) using r.before_row, r.row_id;
        insert into public.ops_r3_rollback_report values (p_op, r.table_name, r.row_id, 'reverted', null);
      end if;
    elsif r.action = 'delete' then
      if public.ops_r3_row_hash(r.table_name, r.row_id) is not null
         or (r.table_name = 'oauth_credentials' and exists (
               select 1 from public.oauth_credentials o where o.account_id = (r.before_row->>'account_id')::uuid)) then
        insert into public.ops_r3_rollback_report values (p_op, r.table_name, r.row_id, 'skipped_conflict',
          'ya existe una fila nueva (p. ej. reconexión)');
      else
        execute format('insert into public.%I select * from jsonb_populate_record(null::public.%I, $1)',
                       r.table_name, r.table_name) using r.before_row;
        insert into public.ops_r3_rollback_report values (p_op, r.table_name, r.row_id, 'reverted', null);
      end if;
    end if;
  end loop;
  alter table public.communication_accounts enable trigger user;
  alter table public.oauth_credentials enable trigger user;
  alter table public.communication_messages enable trigger user;
  update public.ops_r3_operation set status = 'rolled_back', finished_at = now() where op_id = p_op;
  return query select x.outcome, count(*) from public.ops_r3_rollback_report x where x.op_id = p_op group by 1;
end $$;
revoke all on function public.ops_r3_rollback(uuid), public.ops_r3_log(uuid, text, uuid, text, jsonb),
  public.ops_r3_row_hash(text, uuid), public.ops_r3_has_children(text, uuid) from public;
commit;
