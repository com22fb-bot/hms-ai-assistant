-- 001 DOWN: recrea estructura (sin datos; tenían 0 filas)
begin;
create table public.alerts (id uuid default gen_random_uuid() not null, user_id uuid not null, task_id uuid, channel text not null, destination text, message_key text, payload jsonb default '{}'::jsonb not null, scheduled_at timestamp with time zone, sent_at timestamp with time zone, status text default 'PENDING'::text not null, created_at timestamp with time zone default now() not null);
create table public.case_triage_backups (id uuid default gen_random_uuid() not null, run_id uuid not null, case_id uuid not null, before_state jsonb not null, created_at timestamp with time zone default now() not null);
create table public.emails (id uuid default gen_random_uuid() not null, user_id uuid not null, mail_account_id uuid not null, provider_message_id text not null, provider_thread_id text, sender_name text, sender_email text, recipients jsonb default '[]'::jsonb not null, cc jsonb default '[]'::jsonb not null, subject text, body_text text, body_html text, received_at timestamp with time zone, folder text, is_read boolean default false not null, is_starred boolean default false not null, is_archived boolean default false not null, is_deleted boolean default false not null, has_attachments boolean default false not null, requires_response boolean, answered boolean, language text, ai_category text, ai_priority text, ai_summary text, ai_risk text, synchronized_at timestamp with time zone default now() not null);
create table public.ops_r3_operation (op_id uuid default gen_random_uuid() not null, script text not null, started_at timestamp with time zone default now() not null, finished_at timestamp with time zone, status text default 'running'::text not null);
create table public.ops_r3_rollback_report (op_id uuid not null, table_name text not null, row_id uuid not null, outcome text not null, detail text, at timestamp with time zone default now() not null);
create table public.ops_r3_rows (seq bigint not null, op_id uuid not null, table_name text not null, row_id uuid not null, action text not null, before_row jsonb, after_hash text);
create table public.user_workspaces (id uuid default gen_random_uuid() not null, workspace_id uuid not null, user_id uuid not null, role text default 'user'::text not null, created_at timestamp with time zone default now());
alter table public.alerts add constraint alerts_pkey PRIMARY KEY (id);
alter table public.case_triage_backups add constraint case_triage_backups_run_id_case_id_key UNIQUE (run_id, case_id);
alter table public.case_triage_backups add constraint case_triage_backups_pkey PRIMARY KEY (id);
alter table public.emails add constraint emails_pkey PRIMARY KEY (id);
alter table public.emails add constraint emails_mail_account_id_provider_message_id_key UNIQUE (mail_account_id, provider_message_id);
alter table public.ops_r3_operation add constraint ops_r3_operation_pkey PRIMARY KEY (op_id);
alter table public.ops_r3_rows add constraint ops_r3_rows_pkey PRIMARY KEY (seq);
alter table public.user_workspaces add constraint user_workspaces_pkey PRIMARY KEY (id);
alter table public.user_workspaces add constraint user_workspaces_workspace_id_user_id_key UNIQUE (workspace_id, user_id);
alter table public.ops_r3_rows add constraint ops_r3_rows_action_check CHECK ((action = ANY (ARRAY['insert'::text, 'update'::text, 'delete'::text])));
CREATE INDEX idx_emails_user_id ON public.emails USING btree (user_id);
CREATE INDEX idx_emails_received_at ON public.emails USING btree (received_at DESC);
CREATE INDEX ops_r3_rows_op ON public.ops_r3_rows USING btree (op_id, seq);
CREATE INDEX idx_user_workspaces_user ON public.user_workspaces USING btree (user_id);
alter table public.alerts add constraint alerts_task_id_fkey FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE;
alter table public.alerts add constraint alerts_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
alter table public.case_triage_backups add constraint case_triage_backups_case_id_fkey FOREIGN KEY (case_id) REFERENCES intelligent_cases(id) ON DELETE CASCADE;
alter table public.case_triage_backups add constraint case_triage_backups_run_id_fkey FOREIGN KEY (run_id) REFERENCES case_reclassification_runs(id) ON DELETE CASCADE;
alter table public.emails add constraint emails_mail_account_id_fkey FOREIGN KEY (mail_account_id) REFERENCES mail_accounts(id) ON DELETE CASCADE;
alter table public.emails add constraint emails_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
alter table public.ops_r3_rows add constraint ops_r3_rows_op_id_fkey FOREIGN KEY (op_id) REFERENCES ops_r3_operation(op_id);
alter table public.user_workspaces add constraint user_workspaces_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE;
alter table public.user_workspaces add constraint user_workspaces_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
alter table public.tasks add constraint tasks_email_id_fkey FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE SET NULL;
CREATE OR REPLACE FUNCTION public.ops_r3_log(p_op uuid, p_table text, p_id uuid, p_action text, p_before jsonb)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'public'
AS $function$
begin
  insert into public.ops_r3_rows (op_id, table_name, row_id, action, before_row, after_hash)
  values (p_op, p_table, p_id, p_action, p_before,
          case when p_action = 'delete' then null else public.ops_r3_row_hash(p_table, p_id) end);
end $function$
;
CREATE OR REPLACE FUNCTION public.ops_r3_rollback(p_op uuid)
 RETURNS TABLE(outcome text, n bigint)
 LANGUAGE plpgsql
 SET search_path TO 'public'
AS $function$
declare r record; cur text; cols text; collist text; st text;
begin
  -- Concurrencia: un solo rollback a la vez (candado de transacción global) y
  -- la operación se bloquea FOR UPDATE. Una segunda corrida, simultánea o
  -- posterior, espera y luego solo devuelve el reporte: no revierte dos veces.
  perform pg_advisory_xact_lock(hashtextextended('ops_r3_rollback', 0));
  select o.status into st from public.ops_r3_operation o where o.op_id = p_op for update;
  if not found then
    raise exception 'ops_r3_rollback: operación inexistente';
  end if;
  if st = 'rolled_back' then
    return query select x.outcome, count(*) from public.ops_r3_rollback_report x where x.op_id = p_op group by 1;
    return;
  end if;
  set local lock_timeout = '10s';
  -- restaurar valores exactos (incluido updated_at) sin que el trigger los pise
  alter table public.communication_accounts disable trigger user;
  alter table public.oauth_credentials disable trigger user;
  alter table public.communication_messages disable trigger user;
  for r in select * from public.ops_r3_rows where op_id = p_op order by seq desc loop
    -- bloquea la fila objetivo: nadie la cambia entre la comparación y la restauración
    execute format('select 1 from public.%I where id = $1 for update', r.table_name) using r.row_id;
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
        where table_schema = 'public' and table_name = r.table_name and column_name <> 'id'
          and is_generated = 'NEVER';
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
        select string_agg(format('%I', column_name), ', ' order by ordinal_position) into collist
        from information_schema.columns
        where table_schema = 'public' and table_name = r.table_name and is_generated = 'NEVER';
        execute format('insert into public.%I (%s) select %s from jsonb_populate_record(null::public.%I, $1)',
                       r.table_name, collist, collist, r.table_name) using r.before_row;
        insert into public.ops_r3_rollback_report values (p_op, r.table_name, r.row_id, 'reverted', null);
      end if;
    end if;
  end loop;
  alter table public.communication_accounts enable trigger user;
  alter table public.oauth_credentials enable trigger user;
  alter table public.communication_messages enable trigger user;
  update public.ops_r3_operation set status = 'rolled_back', finished_at = now() where op_id = p_op;
  return query select x.outcome, count(*) from public.ops_r3_rollback_report x where x.op_id = p_op group by 1;
end $function$
;
commit;
