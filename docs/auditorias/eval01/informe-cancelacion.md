# EVAL-01 — Informe consolidado de cancelación (30-oct-2026, 17:40 CDMX)

Solo lectura: sin reinicios, despliegues, borrados, migraciones, cambios de datos ni importación. BRAIN_V1_ENABLED y IMPORT_PUSH_NOTIFICATIONS_ENABLED siguen sin definir en Railway (por defecto false). Código desplegado: 90c661b (backend), 41ee15f (frontend).

## 1. Evidencia actual (Supabase, 23:40:51 UTC)
| Dato | Valor |
|---|---|
| Job `99b1445c-370f-486f-841a-8144d9592748` | `cancelled`, `cancel_requested=true` |
| found / inserted / identificados / casos / vinculados / errores | 550 / 550 / 500 / 1 / 0 / 0 |
| next_page_token | 550 (de 735 refs) |
| started / completed | 23:33:21 / 23:36:06 UTC (17:33:21 / 17:36:06 CDMX) |
| Jobs activos en workspace 15c1e9b8 / en toda la BD | 0 / 0 |
| Cuenta `d493c747…` | yahoo, `active` |
| Mensajes de la cuenta / `external_message_id` duplicados | 550 / 0 |
| case_messages / casos del workspace | 1 / 1 |
| push_delivery_log nuevos desde 23:27:05 UTC / `push_notified_at` no nulo | 0 / 0 |
| Gmail hmcelinfo | `active`, 885 mensajes |
Logs: `POST /gmail/import/cancel` 200 a las 23:35:54; el último `phase=download` a las 23:36:06 (lote en curso) y `guided_import cancelled job=99b1445c` a las 23:36:06; nada después.

## 2. Reinicio sin redeploy (propuesto; NO ejecutado)
**Qué hace el arranque** (`backend/main.py:85-102`):
- `resume_durable_gmail_sync_jobs`: solo si `settings.data_mutations_enabled` (hoy /health dice `false` → no hace nada). Si se activara, `resume_incomplete_jobs` (`gmail_sync_job_service.py:576`) solo toma `queued/running/interrupted` y **omite** los que tienen `cancel_requested` o `metadata.guided_import` (l.598).
- `start_automatic_mail_scheduler`: solo procesa cuentas con un inicial guiado `completed` (`_initial_complete`, l.45-56). La cuenta Yahoo no lo tiene (su único job es `cancelled`) → no la toca. Sí corre para el Gmail de hmcelinfo si `HMS_AUTO_SYNC_ENABLED` es true (comportamiento existente, igual que hoy, sin reinicio).
- `start_account_cleanup_scheduler`: limpieza diaria 3:00 CDMX en dry-run salvo `ACCOUNT_CLEANUP_DELETE_ENABLED`.
- La importación guiada solo se reanuda al consultar `/gmail/import/status` o `/start` mediante `_resume_if_needed` → `_is_active(job)` exige estado activo **y** no cancelado (`guided_import_job_service.py:61-70, 576-582`).
**Por qué no reactiva ni duplica:** el job es `cancelled` + `cancel_requested=true`: falla los dos filtros; aunque un hilo arrancara, `_run_job` lanza `_Cancelled` antes de la primera página (l.347). Un job nuevo solo nace con `POST /start` explícito. Pruebas: `test_cancelled_job_is_not_resumed`, `test_cancel_requested_stops_loop_cleanly`, `test_status_cancelled_is_not_overwritten_to_running` (PASSED).
**Riesgos:** corte de unos 10 s de API para todos los usuarios (las peticiones de Héctor y de cualquier otro fallan y reintentan); los hilos en curso de otros usuarios (sincronización automática) se interrumpen y se reanudan desde su último token; los cron de GitHub (respaldo, bitácora, uptime) no dependen del proceso, salvo que uptime podría registrar una caída si coincide.
**Pasos de verificación:** (1) leer el job y confirmar 0 jobs activos; (2) `restart` del deployment 075d5d81 en Railway (sin redeploy); (3) `/health` 200; (4) Héctor abre la app (dispara `/status`); (5) dos lecturas con 1 min de diferencia: estado `cancelled`, contadores y `heartbeat_at` iguales, 0 mensajes nuevos, 0 jobs nuevos, ningún `guided_import timing` en los logs.

## 3. OBS-CANC-01 — los 50 pendientes
- Persistidos: los 550 están en `communication_messages` con `account_id=d493c747…`; 0 duplicados.
- Cómo se distinguen: `case_processed=false` (50 filas; `triage_category='unreviewed'`, `ai_processed=false`, todas creadas a las 23:36:05). Los 500 restantes tienen `case_processed=true`.
- Causa: al cancelar, el hilo de identificación omite los lotes pendientes (`_classifier_worker`, l.302) — comportamiento intencional, pero el panel no lo decía.
- Reintento seguro existente: `classify_pending_messages(account_id, workspace_id, …)` solo selecciona `case_processed=false` (`safe_case_classifier.py`, `.eq("case_processed", False)`), así que reprocesar no toca los 500 ya identificados. Cada mensaje queda `case_processed=true` al procesarse; si falla, se marca `review` con `case_processed=true` y cuenta como error (no se reintenta en bucle).
- Idempotencia: un mensaje procesado no se vuelve a seleccionar, por lo que no se duplican casos ni case_messages **si hay una sola ejecución a la vez** (riesgo de carrera concurrente registrado en #207 CONC-01).
- Conteo: `processed` incluye los rechazados por error (marcados `review`); `errors` los cuenta aparte; `without_case` = procesados sin caso.
- **No usar** `_recover_recent_unprocessed` del programador automático: llama a `notify_actionable_messages` sin pasar por la supresión de push.
- **Estrategia propuesta (sin descargar de nuevo):** "Continuar descarga" crea un job inicial nuevo; `sync_yahoo_page` omite los 550 existentes por `external_message_id` antes de cualquier FETCH (prueba nueva `test_continue_does_not_redownload_existing_messages`: 0 comandos IMAP) y, al completar, el barrido final llama una vez a `classify_pending_messages(limit=1000)` sin `message_ids`, que identifica los 50 y lo que quede (prueba `test_final_sweep_identifies_pending_once`). Esto equivale a la etapa (e) y requiere autorización. Alternativa más acotada: un script local de una sola vez con `message_ids` de los 50 (escritura en producción; requiere autorización).

## 4. OBS-UI-01 / OBS-UI-02 — PR #213 (borrador, NO fusionar)
Rama `fix/import-panel-ui`. Diff resumido:
- `ImportStatusPanel.tsx`: en estado `cancelled` muestra "Descarga detenida…", "{n} descargados aún sin identificar", y los botones **Cerrar** (oculta el panel) y **Continuar descarga** (`POST /gmail/import/start` initial); Cerrar también en `completed`/`failed`; textos es/en; el panel pasa a la esquina inferior **izquierda** para no encimarse con la mascota Nexto (`.nx .bot-dock`, abajo a la derecha), que es lo que aparece junto a la tarjeta de alertas.
- `guided-import.css`: `.hms-logistics-loading::before` y `.hms-import-ready::before` → `content: none` (sin `/hms-import-robot.png`).
- Pruebas: `frontend/lib/importPanelUi.test.ts` 3/3 (añadida al workflow); backend 8/8 en `test_guided_import_cancel_speed.py`; `tsc`, `eslint` y `next build` OK.
- Pendiente de decisión: la mascota Nexto es del asistente de ayuda; no la quité. Si ASTRA/Héctor quieren retirarla del dashboard es otro cambio.

## 5. Límite de 180 días
- Servidor: `import_cutoff_at = 2026-10-30 23:33:10.962 UTC` (17:33:10 CDMX); `history_days=180`; query `yahoo:since:03-May-2026 until:30-Oct-2026`; IMAP `SINCE 03-May-2026` (por fecha, incluye el día completo).
- Filtro exacto para EVAL-01: `received_at >= '2026-05-03 23:33:10.962+00'` (UTC) = **2026-05-03 17:33:10 CDMX** y `received_at <= import_cutoff_at`.
- Resultado sobre los 550: **0** antes del límite (el más antiguo es del 12-may 17:02 UTC); **2** con `received_at` posterior al corte (máx 23:34:15 UTC). Su `received_at` viene de la cabecera `Date`, no de la hora de inserción (0 coincidencias con `created_at`); probable desfase del reloj del remitente o de mensajes que llegaron entre el snapshot de UIDs y la descarga. Se excluyen de lo elegible de EVAL-01 con el filtro anterior → 548 elegibles hasta ahora.

## 6. Decisión propuesta
1. Aprobar el **reinicio aislado** (paso 2) como prueba de no reanudación; lo hago con Héctor sin abrir "Continuar".
2. Desplegar **PR #213** (solo UI y pruebas) tras el reinicio, en una ventana sin importaciones.
3. Autorizar la **etapa (e)** con "Continuar descarga": completa los 185 restantes sin volver a bajar los 550 e identifica los 50 pendientes en el barrido final; luego EVAL-01 aplica el filtro exacto de la sección 5 y el protocolo (muestra de 150, matriz, umbrales).
4. El override expira el 1-nov 17:26:48 CDMX; si la etapa (e) no ocurre antes, hay que renovarlo con autorización.
