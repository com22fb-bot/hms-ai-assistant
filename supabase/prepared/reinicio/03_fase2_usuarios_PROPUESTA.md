FASE 2 (APARTE, OPCIONAL, NO EJECUTADA): usuarios de Auth de los 2 correos de prueba

Requisitos antes de empezar:
- La fase 1 se aplicó en modo 'completo'.
- El PR #126 ya está desplegado. Sin él, al registrarse de nuevo se crea un workspace nuevo, que es justo lo que queremos probar sin duplicados.

Método:
- Borrar con la API de administración de Supabase, desde el panel de Supabase (Authentication → Users → Delete) o con auth.admin.deleteUser(id) usando la service role.
- NO usar DELETE en auth.users por SQL: eso se salta la limpieza de sesiones y refresh tokens que hace GoTrue.
- Ids: dd369e1e… (hmcelinfo@gmail.com) y 4e2a9562… (hsalcidor@yahoo.com). Hay que verificarlos de nuevo con el SELECT de 00_scope.sql justo antes.

Efecto de las cascadas (FK):
- Se borran en cascada: profiles, workspace_members, donexto_preferences, donexto_alert_rules, push_subscriptions, oauth_states, message_*_rules del perfil, hms_notifications del perfil, account_plans y auth.identities.
- Pasan a NULL: workspaces.owner_profile_id, communication_accounts.connected_by_profile_id y case_reclassification_runs.initiated_by.
- Por eso la fase 1 va PRIMERO. Si no, quedan workspaces y buzones huérfanos, que es exactamente el bug actual.

Credenciales:
- Al borrar oauth_credentials en Donexto, el permiso sigue vigente del lado de Google y Yahoo.
- Revocación recomendada, la hace Héctor a mano:
  * Google: myaccount.google.com/permissions → Donexto → Quitar acceso.
  * Yahoo: revocar la contraseña de aplicación.
- Nunca copiar ni exportar tokens.
