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

## Esquemas de respaldo
Solo los que coinciden con `^hms_backup_[a-z0-9_]+$`. Se borran **filas** del usuario (por su id, buzones o mensajes
borrados, o espacios borrados). Nunca se borran esquemas ni tablas, ni se toca ningún otro esquema.

## Storage
Las rutas se encolan en `admin_storage_purge_queue` dentro de la misma transacción (duraderas). El backend borra en lotes
de 100; si falla: `pendiente`, con espera de 30 s × 2^intentos (máx. 1 h); tras 8 intentos queda `fallido` (visible en
`GET /admin/storage-purge`). Reintento manual: `POST /admin/storage-purge/retry`.
La respuesta solo dice `deleted` si Storage terminó; si no, `deleted_storage_pending` y `complete: false`.

## Simulación
`DELETE /admin/users/{id}?dry_run=true` → ejecuta la misma lógica en una subtransacción revertida y devuelve el plan exacto.
La interfaz siempre simula primero y muestra el plan en la confirmación.

## Orden de despliegue
1) aplicar la migración; 2) desplegar el backend. Si el backend llega antes, el borrado **falla cerrado** (409, no borra nada).
