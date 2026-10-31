-- Rollback de 20261031_001_conc01_commit_message.
-- ORDEN OBLIGATORIO: primero desplegar el código anterior (6756abd o el de main) que NO llama a la RPC;
-- después ejecutar este script. Solo retira la función y sus permisos; no toca tablas ni datos
-- y NO deshace procesamientos ya confirmados. Antes de restaurar el CHECK original, normaliza las
-- filas en 'classifying'/'retry_pending' a 'unreviewed' (estado pendiente del código anterior) y
-- guarda la trazabilidad en triage_reason: 'conc01_rollback:<estado previo>:<motivo previo>'.
-- No modifica case_processed ni ninguna otra columna. Después restaura el CHECK original VÁLIDO.
do $$
begin
  if exists (select 1 from pg_catalog.pg_proc p join pg_catalog.pg_namespace n on n.oid = p.pronamespace
                 where n.nspname = 'public' and p.proname = 'conc01_commit_message') then
    revoke all on function public.conc01_commit_message(uuid, uuid, uuid, text, jsonb) from public;
    if exists (select 1 from pg_catalog.pg_roles where rolname = 'service_role') then
      revoke all on function public.conc01_commit_message(uuid, uuid, uuid, text, jsonb) from service_role;
    end if;
  end if;
end $$;
drop function if exists public.conc01_commit_message(uuid, uuid, uuid, text, jsonb);
update public.communication_messages
   set triage_category = 'unreviewed',
       triage_reason = 'conc01_rollback:' || triage_category || ':' || coalesce(triage_reason, '')
 where triage_category in ('classifying', 'retry_pending');
alter table public.communication_messages
  drop constraint if exists communication_messages_triage_category_check;
alter table public.communication_messages
  add constraint communication_messages_triage_category_check check ((triage_category = any (array[
    'unreviewed'::text, 'action_required'::text, 'waiting_external'::text, 'review'::text, 'notice'::text,
    'informational'::text, 'automated'::text, 'promotional'::text, 'social'::text]))) not valid;
alter table public.communication_messages
  validate constraint communication_messages_triage_category_check;
