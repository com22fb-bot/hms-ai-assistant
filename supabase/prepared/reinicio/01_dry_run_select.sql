-- DRY-RUN PURO SELECT (ejecutable en solo lectura). No escribe nada.
with params as (select array['hmcelinfo@gmail.com','hsalcidor@yahoo.com']::text[] emails),
t_users as (select u.id from auth.users u, params p where lower(u.email)=any(p.emails)),
t_acc as (select a.id, a.workspace_id from public.communication_accounts a, params p where lower(a.email)=any(p.emails)),
t_ws as (select w.id from public.workspaces w where w.id in (select workspace_id from t_acc)
   and not exists (select 1 from public.communication_accounts a, params p where a.workspace_id=w.id and lower(coalesce(a.email,''))<>all(p.emails))
   and not exists (select 1 from public.workspace_members m where m.workspace_id=w.id and m.profile_id not in (select id from t_users))),
mixed_ws as (select distinct workspace_id id from t_acc where workspace_id not in (select id from t_ws)),
-- cuentas autorizadas dentro de workspaces mixtos: se pueden borrar como cuenta, nunca el workspace
del_acc as (select id from t_acc)
select 'guard.users_autorizados' item, count(*)::text n from t_users
union all select 'guard.workspaces_mixtos (se conservan)', coalesce(string_agg(left(id::text,8),' '),'0') from mixed_ws
union all select 'guard.cuentas_terceras_en_ws_mixtos', count(*)::text from public.communication_accounts a, params p where a.workspace_id in (select id from mixed_ws) and lower(coalesce(a.email,''))<>all(p.emails)
union all select 'guard.miembros_terceros_en_t_ws', count(*)::text from public.workspace_members m where m.workspace_id in (select id from t_ws) and m.profile_id not in (select id from t_users)
union all select 'guard.mensajes_de_otras_cuentas_en_casos_objetivo', count(*)::text from public.case_messages cm join public.intelligent_cases c on c.id=cm.case_id join public.communication_messages x on x.id=cm.message_id where c.account_id in (select id from del_acc) and x.account_id not in (select id from del_acc)
union all select 'del.communication_accounts', count(*)::text from del_acc
union all select 'del.oauth_credentials', count(*)::text from public.oauth_credentials where account_id in (select id from del_acc)
union all select 'del.communication_threads', count(*)::text from public.communication_threads where account_id in (select id from del_acc)
union all select 'del.communication_messages', count(*)::text from public.communication_messages where account_id in (select id from del_acc)
union all select 'del.intelligent_cases', count(*)::text from public.intelligent_cases where account_id in (select id from del_acc) or workspace_id in (select id from t_ws)
union all select 'del.case_messages', count(*)::text from public.case_messages where case_id in (select id from public.intelligent_cases where account_id in (select id from del_acc) or workspace_id in (select id from t_ws))
union all select 'del.case_events', count(*)::text from public.case_events where case_id in (select id from public.intelligent_cases where account_id in (select id from del_acc) or workspace_id in (select id from t_ws))
union all select 'del.case_participants', count(*)::text from public.case_participants where case_id in (select id from public.intelligent_cases where account_id in (select id from del_acc) or workspace_id in (select id from t_ws))
union all select 'del.case_notifications', count(*)::text from public.case_notifications where case_id in (select id from public.intelligent_cases where account_id in (select id from del_acc) or workspace_id in (select id from t_ws))
union all select 'del.gmail_sync_jobs', count(*)::text from public.gmail_sync_jobs where account_id in (select id from del_acc) or workspace_id in (select id from t_ws)
union all select 'del.hms_notifications', count(*)::text from public.hms_notifications where account_id in (select id from del_acc) or workspace_id in (select id from t_ws)
union all select 'del.push_delivery_log', count(*)::text from public.push_delivery_log where notification_id in (select id from public.hms_notifications where account_id in (select id from del_acc) or workspace_id in (select id from t_ws))
union all select 'del.message_classification_rules', count(*)::text from public.message_classification_rules where account_id in (select id from del_acc) or workspace_id in (select id from t_ws)
union all select 'del.message_watch_rules', count(*)::text from public.message_watch_rules where account_id in (select id from del_acc) or workspace_id in (select id from t_ws)
union all select 'del.case_reclassification_runs', count(*)::text from public.case_reclassification_runs where account_id in (select id from del_acc) or workspace_id in (select id from t_ws)
union all select 'del.reclassification_backup_rows', count(*)::text from public.reclassification_backup_rows where run_id in (select id from public.case_reclassification_runs where account_id in (select id from del_acc) or workspace_id in (select id from t_ws))
union all select 'del.organizational_patterns', count(*)::text from public.organizational_patterns where workspace_id in (select id from t_ws)
union all select 'del.oauth_states', count(*)::text from public.oauth_states where workspace_id in (select id from t_ws)
union all select 'del.push_subscriptions(ws)', count(*)::text from public.push_subscriptions where workspace_id in (select id from t_ws)
union all select 'del.workspace_members', count(*)::text from public.workspace_members where workspace_id in (select id from t_ws)
union all select 'del.workspaces', count(*)::text from t_ws
union all select 'setnull.system_incidents', count(*)::text from public.system_incidents where account_id in (select id from del_acc) or workspace_id in (select id from t_ws)
union all select 'fase2.donexto_preferences(perfil)', count(*)::text from public.donexto_preferences where profile_id in (select id from t_users)
union all select 'fase2.push_subscriptions(perfil)', count(*)::text from public.push_subscriptions where profile_id in (select id from t_users)
union all select 'fase2.profiles', count(*)::text from public.profiles where id in (select id from t_users)
union all select 'fase2.auth.identities', count(*)::text from auth.identities where user_id in (select id from t_users)
union all select 'keep.communication_accounts', (select count(*) from public.communication_accounts)-(select count(*) from del_acc)||''
union all select 'keep.workspaces', (select count(*) from public.workspaces)-(select count(*) from t_ws)||''
union all select 'keep.communication_messages', (select count(*) from public.communication_messages where account_id not in (select id from del_acc))::text;
