-- Rollback de 20261031_001_conc01_commit_message.
-- ORDEN OBLIGATORIO: primero desplegar el código anterior (6756abd o el de main) que NO llama a la RPC;
-- después ejecutar este script. Solo retira la función y sus permisos; no toca tablas ni datos
-- y NO deshace procesamientos ya confirmados.
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
