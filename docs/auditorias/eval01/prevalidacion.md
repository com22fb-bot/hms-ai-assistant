# EVAL-01 — Prevalidación antes de reconectar Yahoo (30-oct-2026, 15:09 CDMX)

Solo lectura. Sin borrados, migraciones, cambios de configuración ni despliegues. Este archivo vive en una rama sin fusionar.

| # | Punto | Estado | Falta |
|---|---|---|---|
| 1 | Commit desplegado y /health | ACREDITADO | — |
| 2 | Cuenta de evaluación inexistente, aislamiento, Gmail intacto | ACREDITADO (estado previo) | El workspace nuevo se verifica al conectar |
| 3 | Ventana de 180 días | PARCIAL | Requiere workspace_id: Héctor inicia sesión → insertar override (escritura autorizada) → leer inventario antes de descargar |
| 4 | Dashboard con sesión | NO ACREDITADO | El panel solo se muestra con un job activo; no hay job sin importar algo |
| 5 | Cancelación y no reanudar | PARCIAL | Pruebas y código sí; falta demostración en vivo (pulsar Detener en la corrida) |
| 6 | BRAIN_V1 apagado y 0 push | ACREDITADO por valores por defecto (las variables no están definidas en Railway); 0 envíos en 48 h | La evidencia por log de supresión no sirve (ver 6) |
| 7 | Logs por fase y errores | PARCIAL | Existen en el código desplegado; aún no se han visto en Railway |

## 1. Commit
- Railway: deployment `075d5d81` SUCCESS, creado 22:41:13 UTC (16:41 CDMX, 29-oct), **commit 90c661b** (merge #212). El anterior, `a74daeb6` (41ee15f), quedó REMOVED.
- `git diff --stat 41ee15f 90c661b` → solo `docs/auditorias/eval01/aceptacion-import.md`. El código del backend es idéntico a 41ee15f.
- Frontend: el workflow "Deploy Donexto app" tiene su última ejecución en **41ee15f** con resultado success; no corrió para 90c661b (solo cambió docs). El bundle publicado contiene "Descargar e identificar casos" y `hms:import-started` (verificado el 29-oct).
- `GET https://api.donexto.com/health` → 200 `{"status":"ok","version":"0.4.6","data_mutations_enabled":false}`.

## 2. Cuentas (Supabase, 21:09 UTC)
```sql
select (select count(*) from auth.users where email ilike '<eval>') auth_eval,
 (select count(*) from profiles where email ilike '<eval>') prof_eval,
 (select count(*) from communication_accounts where email ilike '<eval>') acc_eval,
 (select string_agg(provider||':'||status,',') from communication_accounts where workspace_id='<ws hmcel>') hmcel_accounts,
 (select count(*) from communication_messages where account_id='<cuenta gmail>') hmcel_msgs,
 (select count(*) from workspace_members where workspace_id='<ws hmcel>') hmcel_members, ...
```
Resultado: auth_eval 0, prof_eval 0, acc_eval 0; hmcel_accounts `gmail_imap:active`; hmcel_msgs **885**; hmcel_members 1; jobs activos 0.
- Aislamiento: `admin_purge_user` y la creación de cuenta usan el workspace propio del usuario; el 29-oct la cuenta de evaluación quedó en un workspace distinto (9d8e4e83 ≠ fde232e0). En la nueva corrida se debe repetir la consulta tras conectar.

## 3. 180 días
- Código (90c661b) `account_lifecycle.py:92 _history_override_days`: lee `admin_settings.key='history_days_override:<workspace_id>'` con value JSON `{days, expires_at, reason}`; si `days<=0` o `expires_at <= now()` (l.111) lo ignora; `history_days_for_workspace` lo consulta **antes** que la protección de dueño y que el plan (l.129). Pruebas `test_history_override.py` 3/3.
- Intervalo: `yahoo_import._history_window` → `start = cutoff_at − 180 días` (UTC), `end = cutoff_at` (momento de iniciar). La búsqueda IMAP usa `SINCE <fecha de start>` (granularidad de día, según la zona del servidor de Yahoo); los refs se congelan al iniciar, así que nada posterior a `cutoff_at` entra. El informe debe registrar `import_cutoff_at`, el `history_days` del snapshot y la fecha SINCE usada.
- Expiración: la que se escriba en `expires_at` (propuesta: 48 h). Hoy hay 0 overrides.
- ¿Probar antes de conectar? No del todo: el override necesita el workspace_id, que nace cuando Héctor inicia sesión con la cuenta de evaluación. **Mínimo:** (a) Héctor inicia sesión sin pulsar descargar; (b) se inserta el override (escritura que necesita autorización); (c) con el buzón conectado, `/gmail/import/inventory` o la pantalla debe mostrar 180 días; y en logs aparece `history_days override applied` (WARNING). Solo entonces se pulsa descargar.

## 4. Dashboard
`ImportStatusPanel` solo se hace visible cuando `/gmail/import/status` devuelve un job activo (`visible` se activa con `active`). Con la sesión de hmcelinfo y sin importar nada **no se vería nada** (no hay job activo; el último job ya terminó). No se puede demostrar sin crear un job. Opciones: (a) demostrarlo en la propia corrida EVAL-01 comparando el panel con `gmail_sync_jobs` cada minuto; (b) una descarga incremental del Gmail de hmcelinfo (escritura; no recomendada).

## 5. Cancelación (código 90c661b)
- `_is_cancelled` (l.61) y `_is_active` (l.67); el ciclo lanza `_Cancelled` al inicio (l.347), en cada vuelta (l.361) y antes de completar (l.486); el identificador omite lotes si está cancelado (l.302); `cancel_guided_import` (l.726); `POST /gmail/import/cancel` (`api/guided_import.py:275`); `resume_incomplete_jobs` omite guiados y cancelados (`gmail_sync_job_service.py:598`); `_resume_if_needed` usa `_is_active`.
- Pruebas: 6/6 PASSED en 90c661b (`test_cancel_requested_stops_loop_cleanly`, `test_status_cancelled_is_not_overwritten_to_running`, `test_cancelled_job_is_not_resumed`, …).
- Límite: no hay prueba de reinicio real del proceso; está cubierto por `_is_active` y el filtro de resume.

## 6. Flags y push
- Railway (`list-variables`, solo nombres): **BRAIN_V1_ENABLED no está definida** → por defecto `false` (`brain_v1/__init__.py:13`); **IMPORT_PUSH_NOTIFICATIONS_ENABLED no está definida** → por defecto `False` (`core/config.py:167-171`).
- `push_delivery_log`: 7 en total; **0 en las últimas 48 h**; el último es del 25-oct 01:53 UTC.
- Hallazgo: la línea `guided_import push suppressed` es de nivel INFO y Railway no muestra los INFO de la app (la búsqueda "guided_import" desde el 29-oct 21:15 UTC devuelve 0 líneas, aunque hubo importación). **El 0 push debe acreditarse por BD** (`push_notified_at` nulo y `push_delivery_log` sin filas nuevas), no por ese log. Esto desvía el protocolo §8.

## 7. Logs
Están en el código desplegado como WARNING (sí se ven en Railway): `guided_import timing phase=download … seconds imap_s db_s` (l.471), `phase=identify … n seconds` (l.324), `identify batch failed` (l.328), `final sweep failed` (l.504), `guided_import cancelled` (l.538), `batch fetch failed` (yahoo_import l.591) y `history_days override applied` (account_lifecycle l.114). No se han observado en vivo (aún no hay corrida). La velocidad real también se puede calcular con `gmail_sync_jobs` (`started_at`, `messages_found`, `heartbeat_at`).

## Dictamen
No están acreditados los 7 puntos: falta el 4 y quedan parciales el 3, el 5 y el 7. Según ASTRA, no se reconecta Yahoo sin decisión. Propuesta viable: corrida controlada en la que los puntos 3, 4, 5 y 7 se acreditan **antes de descargar o en los primeros minutos**, con criterios de aborto inmediato.
