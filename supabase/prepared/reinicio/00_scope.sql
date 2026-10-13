-- Alcance común (solo SELECT). Correos autorizados: exactamente estos dos.
with params as (select array['hmcelinfo@gmail.com','hsalcidor@yahoo.com']::text[] emails),
t_users as (select u.id from auth.users u, params p where lower(u.email)=any(p.emails)),
t_acc as (select a.id, a.workspace_id from public.communication_accounts a, params p where lower(a.email)=any(p.emails)),
-- workspace limpio solo si TODAS sus cuentas son autorizadas y TODOS sus miembros (cualquier estado) son usuarios autorizados
t_ws as (select w.id from public.workspaces w where w.id in (select workspace_id from t_acc)
   and not exists (select 1 from public.communication_accounts a, params p where a.workspace_id=w.id and lower(coalesce(a.email,''))<>all(p.emails))
   and not exists (select 1 from public.workspace_members m where m.workspace_id=w.id and m.profile_id not in (select id from t_users))),
-- workspaces con cuentas autorizadas MEZCLADAS con terceros: se omiten (y si la política es abortar, el script real aborta)
mixed_ws as (select distinct workspace_id id from t_acc where workspace_id not in (select id from t_ws))
