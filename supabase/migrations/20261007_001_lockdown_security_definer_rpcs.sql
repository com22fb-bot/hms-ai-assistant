-- Bloquea las funciones SECURITY DEFINER que el linter de Supabase marcó como
-- ejecutables sin sesión (anon) y por cualquier usuario autenticado vía
-- /rest/v1/rpc. Solo el backend (llave secreta => rol service_role) las usa.
--
-- Llamadores encontrados (7 oct 2026):
--   * hms_mail_threads: backend/app/services/message_repository.py con el
--     cliente de SUPABASE_SECRET_KEY (service_role). Ningún llamador en
--     frontend/ ni landing/.
--   * donexto_account_exists: sin llamadores en el repo. Permitía saber si un
--     correo tiene cuenta Donexto (enumeración de correos) sin sesión.
--   * cleanup_unverified_users: sin llamadores ni pg_cron. Borra de auth.users
--     las cuentas sin confirmar de más de 7 días; no debe poder dispararla anon.
--
-- No cambia el cuerpo ni el search_path: las tres ya tienen search_path fijo
-- (public, auth / auth, public / public, extensions).
-- REVOKE ... FROM PUBLIC solo no basta: Supabase da EXECUTE explícito a anon y
-- authenticated por default privileges, por eso se revoca a los tres.

revoke execute on function public.cleanup_unverified_users()
  from public, anon, authenticated;
grant execute on function public.cleanup_unverified_users()
  to service_role;

revoke execute on function public.donexto_account_exists(text)
  from public, anon, authenticated;
grant execute on function public.donexto_account_exists(text)
  to service_role;

revoke execute on function public.hms_mail_threads(
  uuid, uuid, text, text, text, boolean, integer, integer
) from public, anon, authenticated;
grant execute on function public.hms_mail_threads(
  uuid, uuid, text, text, text, boolean, integer, integer
) to service_role;
