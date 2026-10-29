# Paquete de aceptación — importación guiada (29-oct-2026)

- **Commit publicado:** `41ee15f` (merge PR #211). Railway deployment `a74daeb6` SUCCESS (16:38 CDMX); frontend "Deploy Donexto app" success. `/health` 200 (`status ok`).
- **Sin migraciones.** BRAIN_V1_ENABLED=false; IMPORT_PUSH_NOTIFICATIONS_ENABLED=false.

## Cancelación (pruebas `backend/tests/test_guided_import_cancel_speed.py`, 6/6 pasan; suite 822 pasan, 2 fallas previas ajenas en test_microsoft_oauth)
- `cancel_requested=true` a mitad → el ciclo se detiene tras la página en curso; status `cancelled` (no vuelve a `running`).
- `status='cancelled'` externo → no se sobrescribe; 1 sola página.
- Jobs cancelados (o con `cancel_requested`) no se reanudan (`_resume_if_needed`, `resume_incomplete_jobs`).
- Endpoint `POST /gmail/import/cancel` (solo la cuenta del usuario autenticado). En vivo responde 403 sin sesión (ruta existe).
- Pendiente de evidencia en vivo: pulsar "Detener descarga" durante EVAL-01 y anotar 2 lecturas con 1 min de diferencia.

## Rendimiento
- Antes (producción, 29-oct 15:19–15:24 CDMX): **~35 msg/min** extremo a extremo (lotes de 25 ≈ 40–45 s; descarga y clasificación en serie, 1 UID FETCH por mensaje, 1 INSERT por mensaje).
- Después, benchmark sintético de descarga (`bench/bench_yahoo_download.py`, latencias simuladas IMAP 0.12 s/comando, login 1 s, BD 0.04 s/llamada, 200 mensajes): **214 → 554 msg/min (x2.6)** solo en descarga. El costo restante es la creación de hilo por mensaje (2 llamadas BD).
- La identificación ahora corre en paralelo (no bloquea la descarga). **La meta x5 extremo a extremo no está demostrada**: depende del costo real de identificación, que se medirá en EVAL-01 con los logs `guided_import timing phase=download|identify` (segundos por lote, imap_s, db_s).

## Dashboard (estado real)
- `ImportStatusPanel` lee `/gmail/import/status` cada 2.5 s (datos del job en servidor): n de N, %, ritmo (msg/min desde `started_at`), ETA, identificados, casos creados y últimos 8 casos (`intelligent_cases` desde el inicio del job), incidencias.
- Estados reales: `interrupted` (reinicio del servicio) con último error; sin heartbeat >90 s; pérdida de conexión del navegador; `failed` con mensaje y último error; `cancelled`; `completed`.
- Al pulsar "Descargar e identificar casos" el asistente se cierra y se vuelve directo al dashboard. Sin robot ni "Preparando tu correo". Textos es/en.
- Verificado en app.donexto.com: el bundle publicado contiene el botón nuevo y el panel. Demostración con datos de la corrida EVAL-01 pendiente (se anexarán capturas).

## Ventana de 180 días
Override `admin_settings.history_days_override:<workspace_id>` (PR #210). Se inserta en cuanto Héctor conecte la cuenta y antes de pulsar descargar; se verifica `history_days=180` en el snapshot del job y la línea `history_days override applied`. Pendiente de evidencia.

## 0 push
Por diseño (`_notify_or_suppress`); prueba `test_completes_and_classifies_everything_without_push`. En vivo: `push_notified_at` nulo en todos los mensajes del usuario de evaluación (se reportará).

## Borrado previo
Ver `borrado-2026-10-29.md`.
