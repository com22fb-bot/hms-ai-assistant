# Motor y Cerebro IA de Donexto — Diseño P3 (BORRADOR)

23-oct-2026 · Solo documento: no se aplicó nada. `BRAIN_V1_ENABLED` y `HMS_AUTO_SYNC_ENABLED` siguen apagados.
Base: código de `main` (8053ef67) y catálogo de Supabase leído en solo lectura el 23-oct-2026. Los supuestos no verificados van marcados **[SUPUESTO]**.

## 0. Principios
1. Primero los metadatos y el cuerpo después: descargar solo lo necesario y con exclusiones antes de bajar.
2. Separar lo **observado**, que es un hecho con su procedencia, de lo **inferido**, que lleva una confianza, y de lo **confirmado**, que cerró el usuario o una regla.
3. Todo es idempotente: cada paso se puede repetir sin duplicar mensajes, casos, eventos ni avisos.
4. Ningún cambio de modelo entra sin una prueba reproducible y un criterio de aceptación por categoría.

## 1. Flujo de extremo a extremo
```
[A] Buzón conectado (OAuth/IMAP)
 → [B] Trabajo de sync (lease, página, cursor, reintentos)
 → [C] Metadatos del mensaje (ids, cabeceras, fecha, remitente, etiquetas) + exclusiones
 → [D] Cuerpo/adjuntos selectivos (solo si C lo pide)
 → [E] Normalización (asunto, dirección, claves de correlación)
 → [F] Clasificación v2 (área, sombrero, etiquetas de seguridad, confianza)
 → [G] Extracción con procedencia (fechas, importes+moneda, referencias, vencimientos)
 → [H] Correlación → crear | relacionar | actualizar caso
 → [I] Estado del caso: pendiente / confirmado / resuelto / cerrado (+ reglas de confianza)
 → [J] Alertas de seguridad/fraude
 → [K] Avisos idempotentes (in-app/push)
 → [L] Evaluación y aprendizaje (correcciones humanas sin reentrenar en automático)
```

| Paso | Hoy en el código (evidencia) | Objetivo P3 | Contrato de datos (entrada → salida) |
|---|---|---|---|
| A | `communication_accounts` (provider, address_key, status); tokens en `oauth_credentials`; `services/microsoft_oauth.py`, `yahoo_oauth.py`, `imap_mail.py:open_imap_client` | Sin cambios de fondo; un buzón vivo por dirección | cuenta{id, workspace_id, provider, address_key, status} |
| B | `services/gmail_sync_job_service.py`: `create_sync_job` L179, `start_sync_job` L293, `resume_incomplete_jobs` L576; tabla `gmail_sync_jobs` (lease_expires_at, heartbeat_at, retry_count, next_page_token, duplicates, errors); único parcial `uq_gmail_sync_jobs_active_account` | Un solo `sync_jobs` multiproveedor (Gmail/Graph/IMAP) con cursor por proveedor y error tipificado (`import_failure.py:failure_reason` L28) | job{account_id, provider, cursor, lease, intentos, contadores, last_error_code} |
| C | `gmail_sync.py:_get_message_references` L267, `_parse_received_at` L215, `_build_incremental_query` L249; `gmail_full_sync.py:sync_gmail_page` L80; `microsoft_import.py:sync_microsoft_page` L352; `imap_mail.py:list_inbox_messages` L168 | Una etapa común de metadatos por proveedor; exclusiones **antes** de descargar el cuerpo (p2-06) | meta{external_message_id, internet_message_id, in_reply_to, references[], thread_ext_id, from, to/cc, received_at UTC, labels, size, has_attachments} |
| D | `gmail_sync.py:_extract_bodies` L115; `attachments` (filename, mime_type, size, storage_path), con 0 filas | Cuerpo bajo demanda; adjuntos solo los metadatos y la descarga selectiva (p2-12/13) | body{text, html?}, adj{nombre, mime, tamaño, hash} |
| E | `case_engine.py:normalize_subject` L178, `_message_direction` L212; columnas `normalized_subject`, `direction`, `correlation_key` | Igual que hoy, más `content_key` y `ref_key` (ya existen en `brain_signals`, `brain_v1/engine.py` L152/L164) | claves{normalized_subject, correlation_key, content_key, ref_key} |
| F | Vigente: `safe_case_classifier.py:classify_message` L264, `classify_pending_messages` L372, que escribe `triage_category`, `actionability_score`, `triage_reason`. v2 apagada: `brain_v1/taxonomy_v2.py:classify_v2` L307, `AREAS` L14, `SECURITY_TAGS` L61; LLM opcional `brain_v1/llm_fallback.py` (`enabled` L40, `provider` L44) | Taxonomía v2 como única fuente; la regla da el valor previo y el LLM solo actúa como respaldo con límite de costo | clasif{area, sombrero, etiquetas[], regla, confianza 0–1, versión_modelo} |
| G | `brain_v1/dates.py:extract_dates` L243 (zona MX L21, DUE_CUE, RENEWAL_CUE); importes `brain_v1/engine.py` `_REMAINING_RE` L202; legado `ai_analyzer.py:_extract_amounts` L269, `_extract_dates` L297; hoy todo va a `brain_signals` (jsonb) o a `ai_analysis.entities` | **Hechos con procedencia** en filas consultables | hecho{message_id, tipo(fecha_venc, evento, importe, referencia, saldo), valor, moneda, fragmento/offset, extractor+versión, confianza} |
| H | `case_engine.py:_find_case_for_message` L358 (hilo → clave de evento en 7 días → asunto); v1 `brain_v1/engine.py:find_case_v1` L71 (GROUP_WINDOW_DAYS=30, ref_key/content_key); `process_message` L536 y `process_message_v1` L282; enlace `case_messages` (único por message_id) | Correlación por puntaje explicable (hilo, referencia, contenido, remitente+tema, ventana) y **sin fusión automática** por embeddings (p3-12) | decisión{acción: crear/relacionar/actualizar, case_id, puntaje, señales[]} |
| I | `intelligent_cases.status`, `resolved_at`, `closed_at`, `confidence`; `brain_v1/engine.py` STATUS_LABELS L21; `case_user_actions.py` | Máquina de estados explícita: pendiente → confirmado (por el usuario o por una regla con confianza ≥ umbral) → resuelto → cerrado; por debajo del umbral va a «Por revisar» | transición{case_id, de, a, causa, actor, evidencia_ids[]} |
| J | `brain_v1/phishing_v2.py`, `taxonomy_v2.security_tags` L254, `_NO_AREA_FRAUD` L304 | Alertas con evidencia; nunca se cierran solas | alerta{case/message, tipo, severidad, señales[]} |
| K | `push_service.py:create_notification` L297 con dedupe (`.eq("dedupe_key")` L318); `hms_notifications` único (profile_id, dedupe_key); `notify_actionable_messages` L447 | Igual, con dedupe_key = tipo + entidad + versión del hecho | aviso{profile_id, dedupe_key, entidad, canal} |
| L | `learning_engine.py:register_pattern` L23 → `organizational_patterns`; evaluaciones locales L5/L6 (fuera del repo) | Corpus de evaluación versionado; métricas por categoría (precisión, FP/FN, duplicados, cobertura, costo); las correcciones humanas se guardan y no reentrenan solas (p3-19) | corrección{entidad, campo, antes, después, actor}; corrida_eval{versión, métricas} |

Orquestación actual: `automatic_mail_scheduler.py` (apagado por `HMS_AUTO_SYNC_ENABLED`, L24) llama a `classify_pending_messages` L171 → `match_watch_rules_for_account` L178 → `notify_actionable_messages` L179. El sync manual (`api/gmail.py` L199/L236) y `api/cases.py` L44 llaman a `case_engine.process_pending_messages`. El análisis legado va por `api/ai.py` L40 → `ai_analyzer.analyze_pending_messages`. **Hoy hay tres rutas de clasificación en paralelo.** P3 las une en un único pipeline.

## 2. Reglas de confianza (borrador)
| Confianza | Acción |
|---|---|
| ≥ 0.85 y regla determinista | Se asigna el área; el caso puede quedar «confirmado» si además hay referencia o hilo |
| 0.60–0.85 | Se asigna el área; el caso queda «pendiente» |
| < 0.60 o fraude/seguridad | «Por revisar»; nunca se cierra solo; una alerta de seguridad siempre es visible |

Umbrales **[SUPUESTO]**: se calibran con el corpus antes de habilitarlos. La cifra 22/50 = 44 % es una referencia histórica, no el rendimiento actual.

## 3. Tablas actuales: qué conservar, modificar, crear o retirar
Columnas reales leídas del catálogo de prod.

| Tabla / función | Decisión | Justificación por necesidad del motor |
|---|---|---|
| communication_accounts | **Conservar** | Núcleo (A). Unicidad hoy (provider, address_key) para buzones vivos; la de «una dirección» depende de #181 |
| communication_threads | **Conservar** | Único (account_id, external_thread_id); base de la correlación por hilo (H) |
| communication_messages | **Modificar (después)** | Mezcla metadatos, cuerpo, triage legado (`triage_*`, `actionability_score`) y v1 (`brain_*`). Objetivo: separar el resultado de la clasificación en una tabla propia y dejar aquí solo los metadatos y el cuerpo. Se mantienen `ai_processed`/`case_processed` durante la transición |
| intelligent_cases | **Modificar** | Añadir un estado explícito pendiente/confirmado y quitar el triage duplicado (`triage_*` también vive aquí) |
| case_messages | **Conservar** | Único por message_id = un mensaje en un solo caso (deduplicación). `relation_type` ya permite tipar |
| case_events | **Conservar** | Bitácora del caso con dedupe (case_id, dedupe_key); se usará para las transiciones (I) |
| case_participants | Conservar | Participantes por caso |
| gmail_sync_jobs | **Modificar/renombrar** | Ya sirve a todos los proveedores (nombre engañoso); se renombra con una vista de compatibilidad |
| ai_analysis | **Retirar (al final)** | Legado de `ai_analyzer` (summary, category, entities); queda sustituida por la clasificación y los hechos |
| communication_tasks | Revisar | Tareas detectadas; posible reemplazo por los hechos (vencimientos) **[SUPUESTO]** |
| organizational_patterns | Conservar | Aprendizaje por workspace (L) |
| hms_notifications | **Conservar** | Avisos idempotentes (K) |
| attachments | Conservar | Metadatos de adjuntos (D); falta el hash |
| message_watch_rules / _matches, message_classification_rules | Conservar | Reglas del usuario (seguimiento y clasificación) |
| **Nueva: message_classifications** | Crear | (message_id, versión, área, sombrero, etiquetas, regla, confianza, creado_en): historial por versión del modelo para evaluar y comparar |
| **Nueva: extracted_facts** | Crear | Hechos con procedencia (G); hoy están en jsonb sin poder consultarse |
| **Nueva: human_corrections** | Crear | Correcciones auditables (L) |
| **Nueva: eval_runs** | Crear | Métricas por versión y corpus (L) |
| Legado: emails, tasks, alerts, reminders, notifications, users, user_workspaces, mail_accounts, audit_log, ops_r3_*, case_triage_backups | Retirar **solo** tras comprobar consumidores (#184) | No intervienen en el motor; retirarlas no lo desbloquea |

## 4. Matriz de compatibilidad y dependencias
| Componente | Lee/escribe | RLS/permisos | Afectado por P3 | Dependencia de PR |
|---|---|---|---|---|
| Frontend app/admin (Next.js) | Solo `.from("admin_events")` (`app/admin/EventsPanel.tsx`, `OverviewDashboard.tsx`) y `.from("profiles")` (`lib/i18n/LanguageProvider.tsx`); el resto pasa por la API FastAPI | authenticated + políticas | Bajo: consume la API | — |
| API FastAPI (`api/messages.py`, `cases.py`, `sync_jobs.py`, `gmail.py`) | Todas las tablas del motor | service_role (`database/supabase.py`) | Alto: nuevos contratos | — |
| Sync (gmail_sync, gmail_full_sync, microsoft_import, imap_*) | messages, threads, sync_jobs | service_role | Medio: etapa de metadatos común | p2-06/p2-10 |
| Clasificadores (safe_case_classifier, brain_v1, ai_analyzer) | messages, cases, ai_analysis | service_role | Alto: se unifican | — |
| Borrado de cuenta (admin_purge_user) | Todas | SECURITY DEFINER | Debe incluir las tablas nuevas | **#181**: rehacer contra el modelo destino |
| Normalización (#184 001–003) | Retira legado y añade restricciones | — | 003 (FK compuestas, dominios) puede chocar con la nueva separación de clasificación | **#184**: en espera |
| Advisors (#191 004) | Índices de FK y REVOKE | — | Los índices dependen del modelo destino | **#191**: en espera; el REVOKE se extrajo a **#193** |
| REVOKE urgente (#193) | Solo GRANT | anon/authenticated | Ninguno: es independiente | Ninguna |

## 5. Plan de migración (borrador, sin aplicar)
1. **M0 · Evaluación primero:** crear `eval_runs` y un corpus versionado (sintético L6 más una muestra autorizada). Sin cambios de comportamiento.
2. **M1 · Tablas nuevas aditivas:** `message_classifications`, `extracted_facts`, `human_corrections`. Solo service_role, con RLS y sin políticas para anon. El pipeline escribe en **doble vía**, en las columnas viejas y en las tablas nuevas.
3. **M2 · Estado explícito de casos:** columna o enum nuevo con un valor por defecto calculado desde `status`; la vista de compatibilidad mantiene la API.
4. **M3 · Pipeline único** detrás de una bandera nueva (apagada); se compara contra la versión de referencia sobre el corpus.
5. **M4 · Cambio de lectura:** la API lee de las tablas nuevas; las columnas viejas quedan solo para escritura durante 2 semanas **[SUPUESTO]**.
6. **M5 · Retiro:** `ai_analysis`, columnas `triage_*`/`brain_*` y el legado de #184, cada uno con su lista de consumidores en cero y un respaldo previo.

Recuperación: cada paso con up/down probados en Postgres 17 efímero restaurado del respaldo (procedimiento en `docs/ops/RECUPERACION_BD.md`), más un respaldo inmediato antes de aplicar y la autorización expresa de Héctor.

## 6. Evidencia de contraste (código y BD reales)
- Sync: `backend/app/services/gmail_sync.py` (`_find_existing_message` L315: dedupe por account_id + external_message_id; `_get_or_create_thread` L335; `sync_gmail_messages` L435), `gmail_full_sync.py:_existing_message_ids` L56, `gmail_sync_job_service.py` L98–L576, `microsoft_import.py` L214–L352, `imap_mail.py` L76/L168, `import_failure.py` L28–L69.
- Casos: `backend/app/services/case_engine.py` (`_brain_v1_on` L172, `_classify_case_type` L246, `_risk_and_priority` L314, `_find_case_for_message` L358, `_upsert_participant` L434, `_update_learning` L501, `process_message` L536, `process_pending_messages` L828); tablas usadas: intelligent_cases (5 accesos), case_participants (3), communication_messages (2), case_messages (1).
- Cerebro v1: `brain_v1/engine.py` (`find_case_v1` L71, `process_message_v1` L282, `classify_pending_messages_v1` L510; consultas `brain_signals->>ref_key` L152 y `->>content_key` L164; escritura de `brain_confidence`/`brain_signals` L554), `brain_v1/taxonomy_v2.py` (`classify_v2` L307), `brain_v1/dates.py` (`extract_dates` L243), `brain_v1/llm_fallback.py` (OPENAI/GEMINI, L31–L57).
- Legado: `ai_analyzer.py` (`analyze_message_with_openai` L844, `_save_analysis` L977, `analyze_pending_messages` L1119), `safe_case_classifier.py` (L264, L372).
- Avisos: `push_service.py` (`create_notification` L297, dedupe L318), `message_watch_service.py` (`match_watch_rules_for_account` L196).
- Banderas: `brain_v1/__init__.py` L13 (`BRAIN_V1_ENABLED`, por defecto false), `automatic_mail_scheduler.py` L24 (`HMS_AUTO_SYNC_ENABLED`, por defecto false).
- BD (solo lectura, 23-oct-2026): columnas reales de communication_messages (36 columnas, incl. triage_*, brain_confidence, brain_signals, correlation_key, case_processed), intelligent_cases (incl. status, confidence, triage_*, event_at), gmail_sync_jobs (lease_expires_at, retry_count, max_retries, duplicates, selection_categories), case_events (dedupe_key). Únicos: messages(account_id, external_message_id), threads(account_id, external_thread_id), case_messages(message_id), case_events(case_id, dedupe_key) parcial, gmail_sync_jobs(account_id) parcial para estados activos, hms_notifications(profile_id, dedupe_key).
- Datos: hoy prod tiene 0 mensajes, 0 buzones y 0 trabajos; no hay datos reales para medir.

## 7. Supuestos no verificados
- Umbrales de confianza (§2) y duración de la doble escritura (M4).
- Que `communication_tasks` pueda sustituirse por hechos.
- Rendimiento del pipeline único con 3,000+ mensajes por buzón.
- Que el uso de una muestra real requiera autorización explícita de Héctor (se asume que sí).
