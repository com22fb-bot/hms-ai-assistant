begin;
update public.communication_messages m
set direction = b.old_direction, updated_at = now()
from public.ops_r3_direction_backup b
where b.message_id = m.id;
drop table public.ops_r3_direction_backup;
commit;
