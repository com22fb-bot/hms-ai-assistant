-- Ronda 3 · las funciones ops_r3_* y el trigger no deben ser invocables desde la API.
-- Supabase da EXECUTE directo a anon/authenticated/service_role; revocar de public no basta.
revoke execute on function public.ops_r3_rollback(uuid), public.ops_r3_log(uuid, text, uuid, text, jsonb),
  public.ops_r3_row_hash(text, uuid), public.ops_r3_has_children(text, uuid),
  public.hms_r3_deactivate_orphan_accounts()
  from anon, authenticated, service_role;
