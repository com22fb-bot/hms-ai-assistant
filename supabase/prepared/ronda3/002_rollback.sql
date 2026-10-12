-- Revierte 002b (y deja el mapa para auditoría). Orden inverso a las FK.
begin;
delete from public.case_messages where id in (select row_id from public.ops_r3_inserted where table_name='case_messages');
delete from public.case_participants where id in (select row_id from public.ops_r3_inserted where table_name='case_participants');
delete from public.case_events where id in (select row_id from public.ops_r3_inserted where table_name='case_events');
delete from public.intelligent_cases where id in (select row_id from public.ops_r3_inserted where table_name='intelligent_cases');
delete from public.communication_messages where id in (select row_id from public.ops_r3_inserted where table_name='communication_messages');
delete from public.communication_threads where id in (select row_id from public.ops_r3_inserted where table_name='communication_threads');
insert into public.oauth_credentials select * from public.ops_r3_oauth_backup on conflict do nothing;
update public.communication_accounts a set status = m.old_status, updated_at = now()
from public.ops_r3_merge_map m where m.old_account_id = a.id and a.status = 'superseded';
drop table public.ops_r3_inserted, public.ops_r3_case_map, public.ops_r3_oauth_backup;
commit;
