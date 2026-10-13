-- Datos sintéticos que imitan la forma de prod (sin datos reales)
insert into auth.users(id,email) values ('00000000-0000-0000-0000-0000000000a1','hmcelinfo@gmail.com'),('00000000-0000-0000-0000-0000000000a2','hsalcidor@yahoo.com'),('00000000-0000-0000-0000-0000000000b1','tercero@hotmail.com');
insert into auth.identities(user_id,provider) select id,'email' from auth.users;
insert into public.profiles(id) select id from auth.users;
-- W1 viva hmcel, W2/W3 huérfanas hmcel, WM mixta (hmcel + tercero), WY viva yahoo, WY2 huérfana yahoo, WT tercero vivo, WE vacía sin dueño
insert into public.workspaces(id,name,owner_profile_id) values
 ('10000000-0000-0000-0000-000000000001','W1','00000000-0000-0000-0000-0000000000a1'),
 ('10000000-0000-0000-0000-000000000002','W2',null),('10000000-0000-0000-0000-000000000003','W3',null),
 ('10000000-0000-0000-0000-00000000000d','WM',null),
 ('10000000-0000-0000-0000-000000000004','WY','00000000-0000-0000-0000-0000000000a2'),
 ('10000000-0000-0000-0000-000000000005','WY2',null),
 ('10000000-0000-0000-0000-000000000006','WT','00000000-0000-0000-0000-0000000000b1'),
 ('10000000-0000-0000-0000-000000000007','WE',null);
insert into public.workspace_members(workspace_id,profile_id,role,status) values
 ('10000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-0000000000a1','owner','active'),
 ('10000000-0000-0000-0000-000000000004','00000000-0000-0000-0000-0000000000a2','owner','active'),
 ('10000000-0000-0000-0000-000000000006','00000000-0000-0000-0000-0000000000b1','owner','active');
insert into public.communication_accounts(id,workspace_id,provider,provider_account_id,email,status) values
 ('20000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000001','google','g1','hmcelinfo@gmail.com','active'),
 ('20000000-0000-0000-0000-000000000002','10000000-0000-0000-0000-000000000002','google','g1','HMCELINFO@gmail.com','active'),
 ('20000000-0000-0000-0000-000000000003','10000000-0000-0000-0000-000000000003','google','g1','hmcelinfo@gmail.com','active'),
 ('20000000-0000-0000-0000-00000000000d','10000000-0000-0000-0000-00000000000d','google','g1','hmcelinfo@gmail.com','active'),
 ('20000000-0000-0000-0000-00000000000e','10000000-0000-0000-0000-00000000000d','google','g9','otro@gmail.com','active'),
 ('20000000-0000-0000-0000-000000000004','10000000-0000-0000-0000-000000000004','yahoo','y1','hsalcidor@yahoo.com','active'),
 ('20000000-0000-0000-0000-000000000005','10000000-0000-0000-0000-000000000005','yahoo','y1','hsalcidor@yahoo.com','active'),
 ('20000000-0000-0000-0000-000000000006','10000000-0000-0000-0000-000000000006','microsoft','m1','tercero@hotmail.com','active');
insert into public.oauth_credentials(account_id) select id from public.communication_accounts;
insert into public.communication_threads(id,account_id,external_thread_id) select gen_random_uuid(), a.id, 't'||g from public.communication_accounts a, generate_series(1,5) g;
insert into public.communication_messages(account_id,thread_id,external_message_id) select t.account_id,t.id,'m'||t.external_thread_id from public.communication_threads t;
insert into public.intelligent_cases(id,workspace_id,account_id,title) select gen_random_uuid(),workspace_id,id,'caso' from public.communication_accounts;
insert into public.case_messages(case_id,message_id) select c.id,(select m.id from public.communication_messages m where m.account_id=c.account_id limit 1) from public.intelligent_cases c;
insert into public.case_events(case_id,workspace_id,title,event_type) select id,workspace_id,'e','created' from public.intelligent_cases;
insert into public.case_participants(case_id,email) select id,'p@x.com' from public.intelligent_cases;
insert into public.case_notifications(case_id,workspace_id,title) select id,workspace_id,'n' from public.intelligent_cases;
insert into public.gmail_sync_jobs(workspace_id,account_id,status) select workspace_id,id,'completed' from public.communication_accounts;
insert into public.hms_notifications(workspace_id,account_id,profile_id,notification_type,title,body,dedupe_key) values
 ('10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-0000000000a1','x','t','b','k1'),
 ('10000000-0000-0000-0000-000000000006','20000000-0000-0000-0000-000000000006','00000000-0000-0000-0000-0000000000b1','x','t','b','k2');
insert into public.push_delivery_log(notification_id) select id from public.hms_notifications;
insert into public.system_incidents(incident_code,workspace_id,account_id,component,event_type,summary) values ('I1','10000000-0000-0000-0000-000000000002','20000000-0000-0000-0000-000000000002','sync','x','s'),('I2','10000000-0000-0000-0000-000000000006','20000000-0000-0000-0000-000000000006','sync','x','s');
insert into public.organizational_patterns(workspace_id) values ('10000000-0000-0000-0000-000000000001'),('10000000-0000-0000-0000-000000000006');
insert into public.donexto_preferences(profile_id,workspace_id) values ('00000000-0000-0000-0000-0000000000a1','10000000-0000-0000-0000-000000000001'),('00000000-0000-0000-0000-0000000000b1','10000000-0000-0000-0000-000000000006');
insert into public.case_reclassification_runs(id,workspace_id,account_id) values (gen_random_uuid(),'10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001');
insert into public.reclassification_backup_rows(run_id) select id from public.case_reclassification_runs;
