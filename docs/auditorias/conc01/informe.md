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

## Revalidación (hallazgo ASTRA sobre d2d0848)
- postgrest-py 2.31.0: `update()` usa `returning=ReturnMethod.representation` por defecto (`_sync/request_builder.py:418`, cabecera en `base_request_builder.py:198`); `minimal` → 204 sin cuerpo (`data=[]`).
- PostgREST 12.2.3 local (comprobado con curl y log SQL): los filtros lógicos `or=` se reaplican a las filas devueltas por el UPDATE. El filtro de reclamación usa las columnas que cambia, así que `data=[]`/`count=0` aunque la fila se actualizó. Con d2d0848 + PostgREST real: 0 de 50 clasificados, 50 en `classifying`.
- Corrección (ddd3ae3): testigo único en `triage_reason` + `returning=minimal` + SELECT de confirmación por id y testigo.
- Pruebas: adaptador 12/12; PostgREST real 8 passed/4 skipped (inyección de fallos solo en el adaptador), 10/10 corridas.

## R1/R2 (30-oct-2026)
- R1: `process_pending_messages` (case_engine.py) solo se alcanza por `POST /cases/process`, `POST /gmail/sync`, `/gmail/sync-all` y el job durable de Gmail; todas exigen `HMS_DATA_MUTATIONS_ENABLED` y la función exige `HMS_CASE_ENGINE_ENABLED` (ambas por defecto false; ninguna definida en Railway producción, solo se leyeron nombres). No se modificó.
- R2: fencing con el testigo `triage_reason`: `assert_claim` antes de crear/actualizar caso y de insertar case_message; marcas finales (`case_processed`, triage, retry/review) condicionadas atómicamente a `triage_reason = testigo` y confirmadas por SELECT; `ClaimLost` → el trabajador se retira sin escribir (`lost_claims`).
- Pruebas `test_r2_*` (3 puntos de pausa): fallan 3/3 con 6756abd y pasan con el fix, en adaptador y PostgREST 12.2.3.
