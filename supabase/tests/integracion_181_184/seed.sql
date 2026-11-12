-- Datos sintéticos sobre el esquema de producción (sin datos reales). U = usuario a borrar; O = otro miembro.
insert into auth.users(id,email) values ('00000000-0000-0000-0000-0000000000aa','u@x.test'),('00000000-0000-0000-0000-0000000000bb','o@x.test');
insert into public.profiles(id,updated_at) values ('00000000-0000-0000-0000-0000000000aa',now()),('00000000-0000-0000-0000-0000000000bb',now());
insert into public.workspaces(id,name,owner_profile_id,status) values
 ('10000000-0000-0000-0000-000000000001','W1','00000000-0000-0000-0000-0000000000aa','active'),
 ('10000000-0000-0000-0000-000000000002','W2','00000000-0000-0000-0000-0000000000bb','active');
insert into public.workspace_members(workspace_id,profile_id,role,status,created_at,updated_at) values
 ('10000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-0000000000aa','owner','active',now(),now()),
 ('10000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-0000000000bb','owner','active',now(),now()),
 ('10000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-0000000000aa','operator','active',now(),now());
insert into public.communication_accounts(id,workspace_id,provider,status,email,address_key,connected_by_profile_id) values
 ('20000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000001','google','active','u@x.test','u@x.test','00000000-0000-0000-0000-0000000000aa'),
 ('20000000-0000-0000-0000-000000000002','10000000-0000-0000-0000-000000000002','yahoo','active','team@x.test','team@x.test','00000000-0000-0000-0000-0000000000aa');
insert into public.oauth_credentials(account_id) values ('20000000-0000-0000-0000-000000000001'),('20000000-0000-0000-0000-000000000002');
insert into public.communication_threads(id,account_id,external_thread_id) values
 ('30000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001','t1'),
 ('30000000-0000-0000-0000-000000000002','20000000-0000-0000-0000-000000000002','t2');
insert into public.communication_messages(account_id,thread_id,external_message_id)
 select a, t, 'm'||a||g from (values ('20000000-0000-0000-0000-000000000001'::uuid,'30000000-0000-0000-0000-000000000001'::uuid),
                                    ('20000000-0000-0000-0000-000000000002'::uuid,'30000000-0000-0000-0000-000000000002'::uuid)) v(a,t), generate_series(1,4) g;
insert into public.attachments(message_id,storage_path) select id,'u/'||id from public.communication_messages where account_id='20000000-0000-0000-0000-000000000001';
insert into public.gmail_sync_jobs(workspace_id,account_id,created_at,updated_at) values ('10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001',now(),now());
