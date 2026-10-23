-- U = usuario a borrar; O = otro miembro (dueño del espacio compartido); A = admin.
-- W1 = espacio solo de U; W2 = espacio compartido (dueño O); W3 = compartido con dueño U.
insert into auth.users values ('00000000-0000-0000-0000-0000000000aa','u@x.test'),('00000000-0000-0000-0000-0000000000bb','o@x.test'),
  ('00000000-0000-0000-0000-0000000000cc','a@x.test'),('00000000-0000-0000-0000-0000000000dd','p@x.test');
insert into auth.identities(user_id) values ('00000000-0000-0000-0000-0000000000aa');
insert into public.profiles(id,email) select id,email from auth.users;
insert into public.admin_allowlist(user_id) values ('00000000-0000-0000-0000-0000000000cc');
insert into public.workspaces values ('10000000-0000-0000-0000-000000000001','W1','00000000-0000-0000-0000-0000000000aa'),
  ('10000000-0000-0000-0000-000000000002','W2','00000000-0000-0000-0000-0000000000bb'),
  ('10000000-0000-0000-0000-000000000003','W3','00000000-0000-0000-0000-0000000000aa');
insert into public.workspace_members(workspace_id,profile_id,role,joined_at) values
  ('10000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-0000000000aa','owner','2026-01-01'),
  ('10000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-0000000000bb','owner','2026-01-01'),
  ('10000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-0000000000aa','operator','2026-02-01'),
  ('10000000-0000-0000-0000-000000000003','00000000-0000-0000-0000-0000000000aa','owner','2026-01-01'),
  ('10000000-0000-0000-0000-000000000003','00000000-0000-0000-0000-0000000000dd','viewer','2026-03-01');
-- W1 también tiene un miembro dado de baja: no cuenta como "otro miembro activo".
insert into public.workspace_members(workspace_id,profile_id,role,status) values ('10000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-0000000000bb','viewer','removed');
insert into public.communication_accounts(id,workspace_id,provider,email,status,address_key,connected_by_profile_id) values
  ('20000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000001','google','u@x.test','active','k1','00000000-0000-0000-0000-0000000000aa'),
  ('20000000-0000-0000-0000-000000000002','10000000-0000-0000-0000-000000000002','google','team@x.test','active','k2','00000000-0000-0000-0000-0000000000aa'),
  ('20000000-0000-0000-0000-000000000003','10000000-0000-0000-0000-000000000002','yahoo','o@x.test','active','k3','00000000-0000-0000-0000-0000000000bb'),
  ('20000000-0000-0000-0000-000000000004','10000000-0000-0000-0000-000000000003','google','w3@x.test','active','k4','00000000-0000-0000-0000-0000000000aa');
insert into public.oauth_credentials(account_id) select id from public.communication_accounts;
insert into public.communication_threads select ('3'||substr(id::text,2))::uuid, id from public.communication_accounts;
insert into public.communication_messages(id,thread_id,account_id)
  select gen_random_uuid(), ('3'||substr(a.id::text,2))::uuid, a.id from public.communication_accounts a, generate_series(1,5);
insert into public.attachments(message_id,storage_path) select id, 'u/'||id||'.pdf' from public.communication_messages
  where account_id in ('20000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000002');
insert into public.gmail_sync_jobs(account_id,mode,status) select id,'full','done' from public.communication_accounts;
insert into public.hms_notifications(profile_id,account_id) values ('00000000-0000-0000-0000-0000000000aa','20000000-0000-0000-0000-000000000002'),
  ('00000000-0000-0000-0000-0000000000bb','20000000-0000-0000-0000-000000000002');
insert into public.donexto_preferences(profile_id) values ('00000000-0000-0000-0000-0000000000aa'),('00000000-0000-0000-0000-0000000000bb');
insert into hms_backup_test_20260804.communication_accounts values ('20000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-0000000000aa','10000000-0000-0000-0000-000000000001'),
  ('29999999-0000-0000-0000-000000000009','00000000-0000-0000-0000-0000000000bb',null);
insert into hms_backup_test_20260804.communication_messages select id, account_id from public.communication_messages where account_id='20000000-0000-0000-0000-000000000001';
insert into hms_backup_test_20260804.communication_messages values (gen_random_uuid(),'29999999-0000-0000-0000-000000000009');
insert into otro_esquema.communication_messages values (gen_random_uuid(),'20000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-0000000000aa');
insert into hms_backupX.profiles values ('00000000-0000-0000-0000-0000000000aa');

insert into public.tabla_ajena(user_id,profile_id,account_id,workspace_id,message_id,source_message_id)
  select '00000000-0000-0000-0000-0000000000aa','00000000-0000-0000-0000-0000000000aa','20000000-0000-0000-0000-000000000001',
         '10000000-0000-0000-0000-000000000001', id, id from public.communication_messages where account_id='20000000-0000-0000-0000-000000000001';
insert into hms_backup_test_20260804.tabla_ajena select user_id,profile_id,account_id,workspace_id,message_id from public.tabla_ajena;
