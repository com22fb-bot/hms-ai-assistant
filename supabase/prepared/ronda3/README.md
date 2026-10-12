# Ronda 3 — migraciones PREPARADAS (NO APLICAR)

Estas migraciones NO están en `supabase/migrations/` a propósito: no deben aplicarse
a producción sin la revisión de ASTRA y la aprobación explícita de Héctor.
Se ensayaron en un Postgres local con el esquema de producción (sin datos reales) y
datos sintéticos (`backend/tests/db/`).

Orden:
1. `001_gmail_direction_backfill.sql` (+ `001_rollback.sql`)
2. `002_account_consolidation.sql` (+ `002_rollback.sql`) — fase A: copia lo faltante a la
   cuenta canónica y retira las copias (status `superseded`). No borra nada salvo
   credenciales de filas retiradas, que se respaldan antes en `ops_r3_oauth_backup`.
3. `003_orphan_guards.sql` (+ `003_rollback.sql`) — trigger que desactiva cuentas cuando su
   workspace se queda sin miembros activos.

Verificación: `004_verify.sql` (consultas V1–V5, solo SELECT).
