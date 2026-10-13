-- Seguridad de producción extraída del catálogo (solo lectura, 12-oct-2026):
-- funciones hms_*/updated_at, triggers, RLS, políticas y grants. Sin datos.

CREATE OR REPLACE FUNCTION public.hms_touch_updated_at()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public'
AS $function$
begin
    new.updated_at = timezone('utc', now());
    return new;
end;
$function$;
revoke all on function public.hms_touch_updated_at() from public;
grant execute on function public.hms_touch_updated_at() to public;
grant execute on function public.hms_touch_updated_at() to anon;
grant execute on function public.hms_touch_updated_at() to authenticated;
grant execute on function public.hms_touch_updated_at() to service_role;
CREATE OR REPLACE FUNCTION public.hms_ensure_personal_workspace(target_profile_id uuid)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare
    existing_workspace_id uuid;
    created_workspace_id uuid;
    profile_name text;
    personal_slug text;
begin
    select wm.workspace_id into existing_workspace_id
      from public.workspace_members wm
     where wm.profile_id = target_profile_id
       and wm.status = 'active'
       and wm.deleted_at is null
     order by wm.joined_at asc nulls last, wm.created_at asc
     limit 1;

    if existing_workspace_id is not null then return existing_workspace_id; end if;

    select coalesce(
        nullif(trim(p.full_name), ''),
        split_part(p.email::text, '@', 1),
        'Usuario HMS'
    ) into profile_name
      from public.profiles p
     where p.id = target_profile_id;

    if profile_name is null then
        raise exception 'No existe el perfil HMS %', target_profile_id;
    end if;

    personal_slug := 'personal-' || replace(target_profile_id::text, '-', '');

    insert into public.workspaces (name, slug, status, owner_profile_id)
    values (profile_name || ' — Personal', personal_slug, 'active', target_profile_id)
    on conflict (slug)
    do update set owner_profile_id = coalesce(
        public.workspaces.owner_profile_id,
        excluded.owner_profile_id
    )
    returning id into created_workspace_id;

    insert into public.workspace_members (
        workspace_id, profile_id, role, status, joined_at, deleted_at, updated_at
    ) values (
        created_workspace_id, target_profile_id, 'owner', 'active',
        timezone('utc', now()), null, timezone('utc', now())
    )
    on conflict (workspace_id, profile_id)
    do update set
        role = 'owner', status = 'active',
        joined_at = coalesce(public.workspace_members.joined_at, excluded.joined_at),
        deleted_at = null, updated_at = timezone('utc', now());

    return created_workspace_id;
end;
$function$;
revoke all on function public.hms_ensure_personal_workspace(target_profile_id uuid) from public;
grant execute on function public.hms_ensure_personal_workspace(target_profile_id uuid) to service_role;
CREATE OR REPLACE FUNCTION public.hms_handle_auth_user()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'auth'
AS $function$
begin
    insert into public.profiles (
        id, email, full_name, language, locale, timezone, is_active,
        metadata, created_at, updated_at, deleted_at
    ) values (
        new.id,
        lower(new.email)::citext,
        nullif(trim(coalesce(new.raw_user_meta_data ->> 'full_name', '')), ''),
        coalesce(nullif(trim(new.raw_user_meta_data ->> 'language'), ''), 'es'),
        coalesce(nullif(trim(new.raw_user_meta_data ->> 'locale'), ''), 'es-MX'),
        coalesce(nullif(trim(new.raw_user_meta_data ->> 'timezone'), ''), 'America/Mexico_City'),
        true, '{}'::jsonb,
        coalesce(new.created_at, timezone('utc', now())),
        timezone('utc', now()), null
    )
    on conflict (id)
    do update set
        email = excluded.email,
        full_name = coalesce(excluded.full_name, public.profiles.full_name),
        language = excluded.language,
        locale = excluded.locale,
        timezone = excluded.timezone,
        is_active = true,
        deleted_at = null,
        updated_at = timezone('utc', now());

    perform public.hms_ensure_personal_workspace(new.id);
    return new;
end;
$function$;
revoke all on function public.hms_handle_auth_user() from public;
grant execute on function public.hms_handle_auth_user() to service_role;
CREATE OR REPLACE FUNCTION public.hms_set_updated_at()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public'
AS $function$
begin
    new.updated_at = timezone('utc', now());
    return new;
end;
$function$;
revoke all on function public.hms_set_updated_at() from public;
grant execute on function public.hms_set_updated_at() to service_role;
CREATE OR REPLACE FUNCTION public.hms_is_workspace_member(target_workspace_id uuid)
 RETURNS boolean
 LANGUAGE sql
 STABLE
 SET search_path TO 'public'
AS $function$
    select exists (
        select 1
        from public.workspace_members wm
        where wm.workspace_id = target_workspace_id
          and wm.profile_id = auth.uid()
          and wm.status = 'active'
          and wm.deleted_at is null
    );
$function$;
revoke all on function public.hms_is_workspace_member(target_workspace_id uuid) from public;
grant execute on function public.hms_is_workspace_member(target_workspace_id uuid) to authenticated;
grant execute on function public.hms_is_workspace_member(target_workspace_id uuid) to service_role;
CREATE OR REPLACE FUNCTION public.set_updated_at()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public'
AS $function$
begin
    NEW.updated_at = now();
    return NEW;
end;
$function$;
revoke all on function public.set_updated_at() from public;
grant execute on function public.set_updated_at() to public;
grant execute on function public.set_updated_at() to anon;
grant execute on function public.set_updated_at() to authenticated;
grant execute on function public.set_updated_at() to service_role;
CREATE TRIGGER trg_workspace_updated BEFORE UPDATE ON public.workspaces FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_accounts_updated BEFORE UPDATE ON public.communication_accounts FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_threads_updated BEFORE UPDATE ON public.communication_threads FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_oauth_updated BEFORE UPDATE ON public.oauth_credentials FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_intelligent_cases_updated BEFORE UPDATE ON public.intelligent_cases FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_gmail_sync_jobs_updated_at BEFORE UPDATE ON public.gmail_sync_jobs FOR EACH ROW EXECUTE FUNCTION hms_touch_updated_at();
CREATE TRIGGER trg_system_incidents_updated_at BEFORE UPDATE ON public.system_incidents FOR EACH ROW EXECUTE FUNCTION hms_touch_updated_at();
CREATE TRIGGER trg_hms_profiles_updated_at BEFORE UPDATE ON public.profiles FOR EACH ROW EXECUTE FUNCTION hms_set_updated_at();
CREATE TRIGGER trg_hms_workspace_members_updated_at BEFORE UPDATE ON public.workspace_members FOR EACH ROW EXECUTE FUNCTION hms_set_updated_at();
alter table public.workspaces enable row level security;
alter table public.workspace_members enable row level security;
alter table public.profiles enable row level security;
alter table public.communication_accounts enable row level security;
alter table public.oauth_credentials enable row level security;
alter table public.communication_threads enable row level security;
alter table public.communication_messages enable row level security;
alter table public.gmail_sync_jobs enable row level security;
alter table public.intelligent_cases enable row level security;
alter table public.case_messages enable row level security;
alter table public.case_events enable row level security;
alter table public.case_participants enable row level security;
alter table public.case_notifications enable row level security;
alter table public.message_classification_rules enable row level security;
alter table public.message_watch_rules enable row level security;
alter table public.message_watch_matches enable row level security;
alter table public.donexto_preferences enable row level security;
alter table public.hms_notifications enable row level security;
alter table public.system_incidents enable row level security;
alter table public.case_reclassification_runs enable row level security;
create policy hms_workspaces_select_member on public.workspaces as PERMISSIVE for SELECT to authenticated using (hms_is_workspace_member(id));
create policy hms_workspace_members_select_own on public.workspace_members as PERMISSIVE for SELECT to authenticated using (((profile_id = ( SELECT auth.uid() AS uid)) AND (deleted_at IS NULL)));
create policy hms_profiles_select_self on public.profiles as PERMISSIVE for SELECT to authenticated using (((id = ( SELECT auth.uid() AS uid)) AND (deleted_at IS NULL)));
create policy hms_accounts_select_member on public.communication_accounts as PERMISSIVE for SELECT to authenticated using (hms_is_workspace_member(workspace_id));
create policy donexto_preferences_own on public.donexto_preferences as PERMISSIVE for ALL to authenticated using ((profile_id = auth.uid())) with check ((profile_id = auth.uid()));
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.case_events to service_role;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.case_messages to service_role;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.case_notifications to service_role;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.case_participants to service_role;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.case_reclassification_runs to anon;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.case_reclassification_runs to authenticated;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.case_reclassification_runs to service_role;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.communication_accounts to anon;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.communication_accounts to authenticated;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.communication_accounts to service_role;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.communication_messages to anon;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.communication_messages to authenticated;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.communication_messages to service_role;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.communication_threads to anon;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.communication_threads to authenticated;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.communication_threads to service_role;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.donexto_preferences to authenticated;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.donexto_preferences to service_role;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.gmail_sync_jobs to anon;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.gmail_sync_jobs to authenticated;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.gmail_sync_jobs to service_role;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.hms_notifications to service_role;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.intelligent_cases to service_role;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.message_classification_rules to service_role;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.message_watch_matches to service_role;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.message_watch_rules to service_role;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.oauth_credentials to service_role;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.profiles to anon;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.profiles to authenticated;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.profiles to service_role;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.system_incidents to anon;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.system_incidents to authenticated;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.system_incidents to service_role;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.workspace_members to anon;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.workspace_members to authenticated;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.workspace_members to service_role;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.workspaces to anon;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.workspaces to authenticated;
grant DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE on public.workspaces to service_role;
