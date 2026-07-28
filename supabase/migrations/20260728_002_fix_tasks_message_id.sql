alter table public.tasks
add column if not exists message_id uuid;

alter table public.tasks
drop constraint if exists tasks_message_id_fkey;

alter table public.tasks
add constraint tasks_message_id_fkey
foreign key (message_id)
references public.communication_messages(id)
on delete cascade;

create index if not exists idx_tasks_message_id
on public.tasks(message_id);
