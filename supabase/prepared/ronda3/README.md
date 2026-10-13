# Ronda 3 — migraciones

Lo útil pasó a `supabase/migrations/20261012_00{1,2,3,4}_r3_*.sql`. Las cuatro están
aplicadas en producción una sola vez (12-oct-2026, ~18:45 hora CDMX; `list_migrations`
versiones 20261013004449, …4453, …4457, …4507):
- 001: bitácora `ops_r3_operation`, `ops_r3_rows`, `ops_r3_rollback_report` y funciones
  `ops_r3_log`, `ops_r3_row_hash`, `ops_r3_has_children`, `ops_r3_rollback(op_id)`.
- 002: guarda de buzones huérfanos: trigger `trg_hms_r3_orphan_accounts` en
  `workspace_members` → `hms_r3_deactivate_orphan_accounts()`.
- 003: columna generada `address_key` e índice único parcial
  `ux_comm_accounts_live_address (provider, address_key)` para estados `active`/`needs_reauth`.
- 004: revoca EXECUTE de las funciones `ops_r3_*` a los roles de la API.

El código (`oauth_storage._address_key`) normaliza igual que la columna `address_key`
y, al reconectar, reutiliza la fila viva existente en vez de crear otra.

Se descartaron la consolidación (002a/002b) y el backfill de `direction`:
la base se vació el 12-oct-2026 (con respaldo previo), así que no hay nada que consolidar.

`HMS_AUTO_SYNC_ENABLED=false` en Railway: la sincronización automática sigue apagada.
