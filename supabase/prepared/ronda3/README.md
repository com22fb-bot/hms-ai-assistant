# Ronda 3 — migraciones PREPARADAS (NO APLICAR)

Fuera de `supabase/migrations/` a propósito. No se aplican sin la revisión de ASTRA y la
aprobación explícita de Héctor. Se ensayaron solo en un Postgres local aislado
(`backend/tests/db/`), con datos sintéticos.

## Orden
0. `000_ops_infra.sql`: bitácora `ops_r3_*` (op_id, hash por fila) y `ops_r3_rollback(op_id)`.
1. `001_gmail_direction_backfill.sql`: SENT ⇒ outbound. Rollback: `select * from ops_r3_rollback('<op>')`.
2. `002a_merge_map.sql`: mapa canónico + línea base. No toca datos.
3. Revisión humana del mapa y `approved = true` fila por fila.
4. `002b_apply.sql`: consolidación de las filas aprobadas con canónica.
5. `004_verify.sql`: V1–V5 (solo SELECT).
6. `003_orphan_guards.sql` (+ `003_rollback.sql`).

## Revisión manual: filas sin canónica (`revision_manual_sin_canonica`)
Caso: todas las filas de ese buzón están en workspaces sin miembros, así que no hay dueño vivo.
- No se pueden aprobar. Lo impide el check `ops_r3_auto_requires_canonical`.
- 002b no les quita credenciales ni les cambia el estado.
- Proceso:
  1. Confirmar con Héctor si alguien sigue usando ese buzón.
  2. Si nadie lo usa, desactivar con una operación aparte, registrada en `ops_r3_rows`.
  3. Si alguien lo usa, que lo reconecte desde su cuenta. Así se crea la fila viva y la siguiente corrida tendrá canónica.
- Los grupos con 2 o más filas vivas (usuarios distintos) no entran al mapa. No se fusionan nunca.

## Qué NO migra 002b (se queda en la copia; la copia no se borra)
- `hms_notifications`: avisos push ya enviados por perfil.
- `case_triage_backups`, `ai_analysis`, `attachments`, `tasks`, `communication_tasks`.
- `message_watch_matches`, `gmail_sync_jobs`, `case_reclassification_runs`, `system_incidents`.
- Vínculos caso–mensaje cuyo mensaje canónico ya pertenece a otro caso. `case_messages.message_id` es único global, así que el vínculo original queda en la copia.
- Contadores de participantes ya existentes en el caso canónico. No se suman; solo se agregan los participantes que faltan.
Cualquier purga posterior de copias requiere revisar estas tablas antes.
