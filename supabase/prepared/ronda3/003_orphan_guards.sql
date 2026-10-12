-- RONDA 3 · PREPARADA · NO APLICAR SIN APROBACIÓN
-- Cuando un workspace se queda sin miembros activos (borrado, baja lógica con
-- deleted_at o cambio de status), sus buzones dejan de estar 'active'.
create or replace function public.hms_r3_deactivate_orphan_accounts()
returns trigger
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  ws uuid := coalesce(old.workspace_id, new.workspace_id);
begin
  if not exists (
    select 1 from public.workspace_members m
    where m.workspace_id = ws and m.status = 'active' and m.deleted_at is null
  ) then
    update public.communication_accounts
    set status = 'inactive'
    where workspace_id = ws and status in ('active', 'needs_reauth');
  end if;
  return null;
end;
$$;
revoke all on function public.hms_r3_deactivate_orphan_accounts() from public;
do $$ begin
  if exists (select 1 from pg_roles where rolname = 'anon') then
    revoke all on function public.hms_r3_deactivate_orphan_accounts() from anon, authenticated;
  end if;
end $$;

drop trigger if exists trg_hms_r3_orphan_accounts on public.workspace_members;
create trigger trg_hms_r3_orphan_accounts
after delete or update of status, deleted_at on public.workspace_members
for each row execute function public.hms_r3_deactivate_orphan_accounts();
