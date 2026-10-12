-- RONDA 3 · PREPARADA · NO APLICAR SIN APROBACIÓN
-- Gmail: un mensaje con etiqueta SENT es saliente aunque también tenga INBOX
-- (correos que el usuario se envía a sí mismo). Prod 12-oct: 50 filas afectadas.
begin;
create table if not exists public.ops_r3_direction_backup (
  message_id uuid primary key,
  old_direction text,
  changed_at timestamptz not null default now()
);
insert into public.ops_r3_direction_backup (message_id, old_direction)
select m.id, m.direction
from public.communication_messages m
where m.provider = 'google'
  and m.labels ? 'SENT'
  and not (m.labels ? 'DRAFT')
  and m.direction is distinct from 'outbound'
on conflict (message_id) do nothing;

update public.communication_messages m
set direction = 'outbound', updated_at = now()
from public.ops_r3_direction_backup b
where b.message_id = m.id
  and m.direction is distinct from 'outbound';
commit;
