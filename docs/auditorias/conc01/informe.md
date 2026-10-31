# CONC-01 — Idempotencia y concurrencia de classify_pending_messages (30-oct-2026)

Pruebas: `backend/tests/conc01/` contra un Postgres 18 local desechable con datos sintéticos (hilos reales; cada llamada es una sentencia autocommit, como PostgREST).
Ejecutar: `CONC01_PG_DSN="host=/tmp port=55432 user=postgres dbname=postgres" pytest tests/conc01` (rechaza DSN remotos).

| Prueba | main (antes) | rama fix/conc-01-claim |
|---|---|---|
| 2 trabajadores, mismo mensaje | 2 casos, 1 huérfano | 1 caso, 1 case_message |
| 2 trabajadores, mismos 50 | 33 casos, 8 huérfanos | 25 / 25 |
| 8 trabajadores, 50, sin pausa | 90 casos, 65 huérfanos | 25 / 25 |
| reintento tras proceso muerto | 1 mensaje atascado en pending | 0 pendientes |
| fallo entre caso y vínculo | marcado procesado, caso huérfano, sin reintento | retry_pending visible → reintento reutiliza el caso |
| 2º fallo | — | review final, sin bucle |
case_messages nunca se duplicó (índice único `message_id`); push: 0 en todos.
