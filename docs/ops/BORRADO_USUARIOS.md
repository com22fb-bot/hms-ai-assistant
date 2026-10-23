# Borrado de usuarios desde /admin (v2, PR #181, BORRADOR)

Fuente: `supabase/migrations/20261023_002_admin_purge_user_v2.sql` (NO aplicada). Pruebas: `backend/tests/test_purge_sql.py`
(Postgres real efímero) y `backend/tests/test_admin_purge_storage.py`.

## Política de propiedad, desconexión y conservación
| Caso | Qué pasa |
|---|---|
| P1 Espacio donde el usuario es el único miembro activo (los `removed` o con `deleted_at` no cuentan) | Se borra completo: buzones, hilos, mensajes, adjuntos, credenciales, trabajos, casos, membresías |
| P2 Espacio compartido | NO se borran buzones ni mensajes. Los buzones que conectó el usuario pasan a `disconnected`, se borran **sus** credenciales OAuth y se reasignan al dueño del espacio; si el dueño era el usuario, al miembro activo más antiguo, que pasa a ser el dueño |
| P3 Buzón que conectó en un espacio del que no es miembro | Igual que P2 |
| Filas personales (preferencias, avisos, reglas con `profile_id`) | Se borran siempre |
| Bitácora (`admin_events`) | Se conserva; solo guarda conteos y `purge_ref`, sin correo ni nombre |

## Lista explícita de tablas (`public.admin_purge_targets`)
El borrado ya NO recorre tablas por nombre de columna. Solo limpia estas relaciones, revisadas contra las FK reales
de producción (23-oct-2026). Cualquier otra tabla queda intacta aunque tenga `user_id`, `account_id`, etc.

| Clave | Tablas.columna |
|---|---|
| mensaje (de buzones borrados) | ai_analysis.message_id, attachments.message_id, case_messages.message_id, communication_tasks.message_id, hms_notifications.message_id, message_watch_matches.message_id, message_watch_rules.source_message_id |
| buzón borrado | oauth_credentials, gmail_sync_jobs, intelligent_cases, case_reclassification_runs, message_classification_rules, message_watch_rules, hms_notifications (.account_id) |
| espacio solo del usuario | case_events, case_notifications, communication_tasks, gmail_sync_jobs, intelligent_cases, organizational_patterns, oauth_states (.workspace_id) |
| usuario (profile_id) | donexto_alert_rules, donexto_preferences, hms_notifications, message_classification_rules, message_watch_rules, oauth_states, push_subscriptions |
| usuario (user_id) | account_plans |
| núcleo (orden fijo) | communication_messages, communication_threads, communication_accounts, workspace_members, workspaces, profiles, auth.users |

Excluidas a propósito: admin_events, admin_allowlist, admin_storage_purge_queue, system_incidents (FK SET NULL),
case_events.message_id (FK SET NULL), ops_*, y `communication_accounts.connected_by_profile_id` (P2 conserva el buzón).

## Tablas legadas (compatibilidad con PR #184)
alerts, emails, user_workspaces, notifications, users, reminders, tasks, audit_log y mail_accounts **no** están en la lista
ni en el cuerpo de `_admin_purge_user_exec` (ya no existe `delete from public.users`). PR #184 las elimina (001/002).
Opción elegida (explícita y auditable): sacarlas de la lista y revisarlas aparte en `_admin_purge_legacy_check()` con
`to_regclass()`:
- no existe → `omitida_inexistente` (queda en el plan, campo `legacy`);
- existe sin filas del usuario → `presente_sin_filas`;
- existe con filas del usuario → **aborta** sin borrar nada (hoy todas tienen 0 filas en producción).
Orden: #181 → #184 001 → 003 → 002. La 002 de #184 aborta si falta #181 o si quedan referencias.
Prueba: `supabase/tests/integracion_181_184/run.sh` (CI, job `integracion-181-184`).

## Esquemas de respaldo
Solo los que coinciden con `^hms_backup_[a-z0-9_]+$`, con **la misma lista explícita** (incluidas las tablas núcleo).
Se borran **filas** del usuario (por su id, buzones o mensajes borrados, o espacios borrados). Nunca se borran esquemas ni tablas, ni se toca ningún otro esquema.

## Storage
Las rutas se encolan en `admin_storage_purge_queue` dentro de la misma transacción (duraderas). El backend borra en lotes
de 100; si falla: `pendiente`, con espera de 30 s × 2^intentos (máx. 1 h); tras 8 intentos queda `fallido` (visible en
`GET /admin/storage-purge`). Reintento manual: `POST /admin/storage-purge/retry`.
La respuesta solo dice `deleted` si Storage terminó; si no, `deleted_storage_pending` y `complete: false`.

## Bucket de adjuntos (verificado 23-oct-2026)
- Nombre único: `public.admin_attachments_bucket()` = `attachments`; viaja en cada fila de la cola. El backend no tiene
  otro nombre ni variable de entorno (no existe `ATTACHMENTS_BUCKET` en Doppler ni en el código).
- Producción: `storage.buckets` está **vacío** (0 buckets) y `public.attachments` tiene 0 filas; ningún código escribe
  `attachments.storage_path` ni sube archivos. Hoy no hay archivos que borrar, pero eso **no** valida la integración.
- Falta: cuando se implemente la subida de adjuntos, crear el bucket privado `attachments` (o cambiar la constante SQL).
  Mientras no exista, el plan lo muestra (`storage_bucket_exists: false`) y la cola marca `bucket_inexistente` sin
  declarar éxito ni perder las rutas.

## Simulación
`DELETE /admin/users/{id}?dry_run=true` → ejecuta la misma lógica en una subtransacción revertida y devuelve el plan exacto.
La interfaz siempre simula primero y muestra el plan en la confirmación.

## Orden de despliegue
1) aplicar la migración; 2) desplegar el backend. Si el backend llega antes, el borrado **falla cerrado** (409, no borra nada).
