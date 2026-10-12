-- RONDA 3 · PREPARADA · NO APLICAR SIN APROBACIÓN
-- Cuando un workspace se queda sin miembros activos (usuario borrado desde la app
-- o desde el panel de Supabase), sus buzones dejan de estar 'active'.
create or replace function public.hms_r3_deactivate_orphan_accounts()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  ws uuid := coalesce(old.workspace_id, new.workspace_id);
begin
  if not exists (
    select 1 from public.workspace_members m
    where m.workspace_id = ws and m.status = 'active'
  ) then
    update public.communication_accounts
    set status = 'inactive', updated_at = now()
    where workspace_id = ws and status in ('active', 'needs_reauth');
  end if;
  return null;
end;
$$;
revoke all on function public.hms_r3_deactivate_orphan_accounts() from public, anon, authenticated;

drop trigger if exists trg_hms_r3_orphan_accounts on public.workspace_members;
create trigger trg_hms_r3_orphan_accounts
after delete or update of status on public.workspace_members
for each row execute function public.hms_r3_deactivate_orphan_accounts();
