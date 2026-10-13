# Ronda 3 — migraciones

Lo útil pasó a `supabase/migrations/20261012_00{1,2,3}_r3_*.sql` (aplicadas en producción el 12-oct-2026):
- 001: bitácora `ops_r3_*` y `ops_r3_rollback(op_id)` (seguro con corridas simultáneas).
- 002: guardas de buzones huérfanos (trigger en `workspace_members`).
- 003: índice único parcial: un buzón vivo por proveedor + dirección normalizada.

Se descartaron la consolidación (002a/002b/004) y el backfill de `direction` (001):
la base se vació el 12-oct-2026 (respaldo previo), así que no hay nada que consolidar.
