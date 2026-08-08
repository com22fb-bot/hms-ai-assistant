-- Sprint 4.10: índices y políticas optimizadas para la identidad HMS.

drop index if exists public.uq_hms_workspace_members_pair;

create index if not exists idx_hms_workspaces_owner_profile
on public.workspaces(owner_profile_id)
where owner_profile_id is not null;

create index if not exists idx_hms_accounts_connected_by_profile
on public.communication_accounts(connected_by_profile_id)
where connected_by_profile_id is not null;

create index if not exists idx_hms_oauth_states_profile
on public.oauth_states(profile_id, expires_at)
where profile_id is not null;

drop policy if exists hms_profiles_select_self on public.profiles;
create policy hms_profiles_select_self
on public.profiles for select to authenticated
using (id = (select auth.uid()) and deleted_at is null);

drop policy if exists hms_workspace_members_select_own on public.workspace_members;
create policy hms_workspace_members_select_own
on public.workspace_members for select to authenticated
using (profile_id = (select auth.uid()) and deleted_at is null);
