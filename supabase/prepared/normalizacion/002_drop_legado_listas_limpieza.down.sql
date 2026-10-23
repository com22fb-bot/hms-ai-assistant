-- 002 DOWN
begin;
create table public.audit_log (id uuid default gen_random_uuid() not null, user_id uuid, action text, entity text, entity_id text, old_values jsonb, new_values jsonb, ip text, created_at timestamp with time zone default now());
create table public.mail_accounts (id uuid default gen_random_uuid() not null, user_id uuid not null, provider text not null, email_address text not null, display_name text, access_token_encrypted text, refresh_token_encrypted text, token_expires_at timestamp with time zone, last_sync_at timestamp with time zone, active boolean default true not null, created_at timestamp with time zone default now() not null);
create table public.notifications (id uuid default gen_random_uuid() not null, user_id uuid, channel text, title text, body text, delivered boolean default false, created_at timestamp with time zone default now());
create table public.reminders (id uuid default gen_random_uuid() not null, task_id uuid, remind_at timestamp with time zone, sent boolean default false, created_at timestamp with time zone default now());
create table public.tasks (id uuid default gen_random_uuid() not null, user_id uuid not null, email_id uuid, title text not null, description text, task_type text, status text default 'OPEN'::text not null, priority text default 'MEDIUM'::text not null, due_at timestamp with time zone, assigned_to text, detected_by_ai boolean default false not null, completed_at timestamp with time zone, created_at timestamp with time zone default now() not null, message_id uuid);
create table public.users (id uuid default gen_random_uuid() not null, email text not null, full_name text, password_hash text, status text default 'active'::text, created_at timestamp with time zone default now(), updated_at timestamp with time zone default now());
alter table public.audit_log add constraint audit_log_pkey PRIMARY KEY (id);
alter table public.mail_accounts add constraint mail_accounts_pkey PRIMARY KEY (id);
alter table public.mail_accounts add constraint mail_accounts_user_id_email_address_key UNIQUE (user_id, email_address);
alter table public.notifications add constraint notifications_pkey PRIMARY KEY (id);
alter table public.reminders add constraint reminders_pkey PRIMARY KEY (id);
alter table public.tasks add constraint tasks_pkey PRIMARY KEY (id);
alter table public.users add constraint users_email_key UNIQUE (email);
alter table public.users add constraint users_pkey PRIMARY KEY (id);
CREATE INDEX idx_mail_accounts_user_id ON public.mail_accounts USING btree (user_id);
CREATE INDEX idx_tasks_message_id ON public.tasks USING btree (message_id);
CREATE INDEX idx_tasks_status ON public.tasks USING btree (status);
CREATE INDEX idx_tasks_user_id ON public.tasks USING btree (user_id);
alter table public.mail_accounts add constraint mail_accounts_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
alter table public.notifications add constraint notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);
alter table public.reminders add constraint reminders_task_id_fkey FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE;
alter table public.tasks add constraint tasks_message_id_fkey FOREIGN KEY (message_id) REFERENCES communication_messages(id) ON DELETE CASCADE;
alter table public.tasks add constraint tasks_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
do $$ begin if to_regprocedure('public.set_updated_at()') is not null then
 create trigger trg_users_updated before update on public.users for each row execute function set_updated_at();
 create trigger trg_tasks_updated before update on public.tasks for each row execute function set_updated_at(); end if; end $$;
commit;
