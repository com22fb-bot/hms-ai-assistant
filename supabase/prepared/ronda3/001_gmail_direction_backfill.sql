-- RONDA 3 · PREPARADA · NO APLICAR SIN APROBACIÓN (requiere 000_ops_infra.sql)
-- Gmail: SENT => outbound aunque tenga INBOX (prod 12-oct: 50 filas). Rollback:
-- select * from ops_r3_rollback('<op_id>');  (no pisa filas modificadas después)
do $$
declare v_op uuid; r record;
begin
  insert into public.ops_r3_operation (script) values ('001_gmail_direction_backfill') returning op_id into v_op;
  for r in
    select m.id, to_jsonb(m) as before_row from public.communication_messages m
    where m.provider = 'google' and m.labels ? 'SENT' and not (m.labels ? 'DRAFT')
      and m.direction is distinct from 'outbound'
  loop
    update public.communication_messages set direction = 'outbound' where id = r.id;
    perform public.ops_r3_log(v_op, 'communication_messages', r.id, 'update', r.before_row);
  end loop;
  update public.ops_r3_operation set status = 'done', finished_at = now() where op_id = v_op;
  raise notice 'op_id=%', v_op;
end $$;
