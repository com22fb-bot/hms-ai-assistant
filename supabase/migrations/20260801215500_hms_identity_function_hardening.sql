-- Sprint 4.10: funciones auxiliares con search_path fijo y sin privilegios
-- SECURITY DEFINER innecesarios.

alter function public.set_updated_at() set search_path = public;

create or replace function public.hms_is_workspace_member(target_workspace_id uuid)
returns boolean
language sql
stable
security invoker
set search_path = public
as $$
    select exists (
        select 1
        from public.workspace_members wm
        where wm.workspace_id = target_workspace_id
          and wm.profile_id = auth.uid()
          and wm.status = 'active'
          and wm.deleted_at is null
    );
$$;

grant execute on function public.hms_is_workspace_member(uuid) to authenticated;
