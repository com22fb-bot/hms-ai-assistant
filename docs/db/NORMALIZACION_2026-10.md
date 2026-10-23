# Normalización de la BD Donexto · 23-oct-2026 (CDMX)

Propuesta **no aplicada**. Producción solo se leyó (SELECT a pg_stat_user_tables, pg_constraint, information_schema, pg_indexes, pg_proc).
Migraciones preparadas en `supabase/prepared/normalizacion/` (no están en `supabase/migrations/`, nada las despliega).

## 1. Inventario (public; no hay otros esquemas de app tras borrar los respaldos de agosto)
filas = count real · ins/upd/del = acumulado pg_stat · refs = archivos de código (backend/frontend/workers/scripts) con acceso real

| tabla | filas | KB | FK sal/ent | ins/upd/del | uso |
|---|---|---|---|---|---|
| account_cleanup_runs | 14 | 32 | 0/0 | 14/0/0 | en uso |
| account_plans | 2 | 32 | 1/0 | 2/2/0 | en uso |
| admin_allowlist | 1 | 24 | 1/0 | 1/0/0 | en uso |
| admin_events | 37 | 120 | 0/0 | 40/4/0 | en uso (Bitácora) |
| admin_expenses | 11 | 32 | 0/0 | 11/0/0 | en uso |
| admin_settings | 1 | 32 | 0/0 | 1/0/0 | en uso |
| ai_analysis | 0 | 48 | 1/0 | 1/2/1 | en uso (ai_analyzer) |
| **alerts** | 0 | 16 | 2/0 | 0/0/0 | **sobra**: nunca escrita, sin código |
| attachments | 0 | 24 | 1/0 | 0/0/0 | revisar: cola Storage del #181 la usa |
| **audit_log** | 0 | 16 | 0/0 | 0/0/0 | **sobra**: solo en lista de limpieza; reemplazada por admin_events |
| case_events | 0 | 784 | 3/1 | 2031/14/1937 | en uso |
| case_messages | 0 | 480 | 2/0 | 2031/0/1530 | en uso |
| case_notifications | 0 | 288 | 3/0 | 1300/5/1300 | en uso |
| case_participants | 0 | 440 | 1/0 | 2418/648/2418 | en uso |
| case_reclassification_runs | 0 | 48 | 3/2 | 2/19/2 | en uso |
| **case_triage_backups** | 0 | 24 | 2/0 | 0/0/0 | **sobra**: nunca escrita, sin código |
| communication_accounts | 0 | 112 | 2/10 | 87/403/87 | en uso (núcleo) |
| communication_messages | 0 | 96 | 3/10 | 13591/17113/13422 | en uso (núcleo) |
| communication_tasks | 0 | 80 | 1/0 | 1/0/1 | en uso; **se solapa** con tasks |
| communication_threads | 0 | 1672 | 1/2 | 12740/333/12712 | en uso |
| contact_messages | 4 | 64 | 0/0 | 4/6/0 | en uso |
| donexto_alert_rules | 0 | 24 | 2/0 | 0/0/0 | en uso (preferences_service) |
| donexto_preferences | 2 | 32 | 2/0 | 15/59/13 | en uso |
| **emails** | 0 | 40 | 2/1 | 0/0/0 | **sobra**: modelo v0, reemplazada por communication_messages |
| gmail_sync_jobs | 0 | 256 | 2/1 | 127/804/127 | en uso; nombre engañoso (sirve a todos los proveedores) |
| hms_notifications | 0 | 168 | 5/1 | 133/28/133 | en uso; **se solapa** con notifications/case_notifications |
| intelligent_cases | 0 | 744 | 3/6 | 1237/794/1237 | en uso |
| **mail_accounts** | 0 | 32 | 1/1 | 0/0/0 | **sobra**: v0, reemplazada por communication_accounts (solo un health-check en system.py) |
| message_classification_rules | 0 | 48 | 4/1 | 4/0/4 | en uso |
| message_watch_matches | 0 | 56 | 2/0 | 2/2/2 | en uso |
| message_watch_rules | 0 | 96 | 4/1 | 5/0/5 | en uso |
| **notifications** | 0 | 16 | 1/0 | 0/0/0 | **sobra**: v0, FK a public.users (vacía) |
| oauth_credentials | 0 | 128 | 1/0 | 89/104/89 | en uso |
| oauth_states | 1 | 80 | 2/0 | 287/0/286 | en uso |
| **ops_r3_operation / ops_r3_rows / ops_r3_rollback_report** | 0 | 48 | — | 0/0/0 | **sobran**: operación R3 terminada; rollback_report sin PK |
| organizational_patterns | 0 | 184 | 1/0 | 281/2635/281 | en uso |
| profiles | 2 | 80 | 1/11 | 96/589/91 | en uso (núcleo) |
| push_delivery_log | 0 | 32 | 2/0 | 21/18/21 | en uso |
| push_subscriptions | 1 | 64 | 2/1 | 13/21/12 | en uso |
| reclassification_backup_rows | 0 | 80 | 1/0 | 473/0/473 | en uso |
| **reminders** | 0 | 8 | 1/0 | 0/0/0 | **sobra**: v0 (FK a tasks) |
| system_incidents | 7 | 104 | 3/0 | 113/5/106 | en uso |
| **tasks** | 0 | 40 | 3/2 | 0/0/0 | **sobra**: v0, duplicada por communication_tasks |
| **user_workspaces** | 0 | 32 | 2/0 | 0/0/0 | **sobra**: duplicada por workspace_members |
| **users** (public) | 0 | 24 | 0/2 | 0/0/0 | **sobra**: duplicada por auth.users + profiles |
| workspace_members | 2 | 96 | 2/0 | 96/0/91 | en uso |
| workspaces | 2 | 96 | 1/17 | 96/70/91 | en uso |

Resumen: 49 tablas · 34 en uso · 13 sobran (≈0,4 MB) · 1 en revisión (attachments) · solapes: tasks↔communication_tasks, users↔profiles, user_workspaces↔workspace_members, notifications↔hms_notifications, mail_accounts↔communication_accounts, emails↔communication_messages.

## 2. Las 10 formas normales (veredicto y recomendación)
Leyenda: ✅ cumple · ❌ no cumple · — no aplica / no vale la pena.

**1FN (valores atómicos, sin grupos repetidos)**
- ❌ communication_messages.recipients/cc/bcc/labels/references_header (JSONB-lista), communication_threads.participants (texto con lista), oauth_credentials.scopes, gmail_sync_jobs.selection_categories.
- Pragmático: se quedan en JSONB (se leen siempre junto con el mensaje, nunca se consultan por separado) pero con dominio forzado a arreglo (003). Cuando el Cerebro necesite "todos los correos donde participa X", crear `message_participants(message_id, role, address_key)` → lista C.
- ✅ resto de tablas.

**2FN (sin dependencias parciales de una clave compuesta)**
- ✅ todas usan PK surrogada uuid de una columna. case_participants (case_id,email) y workspace_members (workspace_id,profile_id) son claves candidatas compuestas sin atributos que dependan de solo una parte. ✅.

**3FN (sin dependencias transitivas)**
- ❌ communication_messages.provider y communication_threads.provider dependen de account_id → provider (copia de communication_accounts.provider). C: quitar columnas y leer del buzón.
- ❌ intelligent_cases.workspace_id depende de account_id → workspace_id; communication_messages.account_id depende de thread_id → account_id. Se conservan por rendimiento/RLS, pero 003 añade FK compuestas que garantizan que no se contradigan (B).
- ❌ profiles.email copia auth.users.email (puede divergir). C: trigger de sincronización o leer de auth.
- ❌ intelligent_cases.requester_email/current_owner_email y case_participants.email: correo repetido como texto; C: normalizar a address_key en minúsculas (hoy citext solo en profiles).
- ❌ communication_accounts.address_key derivado de email/provider_account_id: aceptable como columna generada (ya lo es) → ✅ pragmático.

**FNCE / EKNF (clave elemental)**
- ✅ en general: cada dependencia no trivial parte de una clave elemental. Caso dudoso: case_messages tenía 2 claves únicas (message_id) y (case_id,message_id); la segunda no es elemental (redundante). 003 la quita (B).

**FNBC (todo determinante es clave)**
- ❌ communication_accounts: address_key → (buzón vivo) es regla de negocio "un buzón por dirección", pero el índice actual es (provider, address_key) → hmcelinfo tuvo 2 buzones. El #181 ya trae `ux_comm_accounts_live_address_any (address_key)`; no se duplica aquí (aplicarlo con #181).
- ❌ communication_messages: (account_id, external_message_id) es clave ✅; thread_id → account_id sin clave → resuelto con UNIQUE(id,account_id) + FK compuesta (003).
- ✅ resto.

**4FN (sin dependencias multivaluadas independientes)**
- ❌ message_watch_rules / message_classification_rules mezclan account_id, profile_id, workspace_id y source_message_id en una fila (alcance multivaluado). — Pragmático: se deja; es configuración de bajo volumen.
- ✅ case_participants, workspace_members, case_messages ya son tablas puente correctas.

**FNTE / ETNF (tupla esencial)**
- ✅ con 3FN + claves corregidas no quedan tuplas redundantes en el núcleo, salvo las copias de provider (C) y los duplicados legados (A).

**5FN (sin dependencias de reunión)**
- ✅ no hay relaciones ternarias descomponibles en el núcleo. — No se recomiendan más descomposiciones.

**DKNF (dominio/clave)**
- ❌ status/provider en texto libre: communication_accounts.status, communication_accounts.provider, communication_threads.provider, communication_messages.provider, workspaces.status sin CHECK → 003 (B).
- ❌ enums inconsistentes: communication_tasks.status en MAYÚSCULAS ('OPEN'…) vs resto en minúsculas; mezcla ES ('abierto','nuevo') en admin_events/contact_messages vs EN en el resto → C (cambio de código).
- ✅ tablas que ya tienen CHECK: account_plans, admin_events, case_reclassification_runs, contact_messages, gmail_sync_jobs, intelligent_cases, push_delivery_log, system_incidents, workspace_members.

**6FN (una sola dependencia no clave por tabla / historia temporal)**
- — No conviene en OLTP: multiplicaría joins. Solo vale la pena donde ya existe historia temporal: la bitácora de buzón (admin_events / case_events) que pidió Héctor (fechas, horas, procesos) — modelarla como eventos inmutables (ya es así). No se propone migración.

## 3. Otros hallazgos
- communication_accounts.workspace_id ON DELETE NO ACTION: bloquea borrar un espacio con buzones; correcto mientras #181 maneje el borrado explícito.
- ops_r3_rollback_report sin PK (se elimina en A).
- 13 tablas sobrantes ≈ 400 KB: el ahorro de espacio es mínimo; el beneficio es claridad y menos riesgo en borrados.

## 4. Listas para confirmación de Héctor
**A · DROP** (migr. 001 y 002; guardia aborta si alguna tiene filas; down recrea estructura)
- 001 (sin código): alerts, emails, user_workspaces, case_triage_backups, ops_r3_operation, ops_r3_rows, ops_r3_rollback_report (+ funciones ops_r3_log, ops_r3_rollback).
- 002 (requiere C1 antes): users, notifications, tasks, reminders, audit_log, mail_accounts.

**B · Estructura** (migr. 003, sin cambio de código)
- CHECK de status/provider en communication_accounts, threads, messages y workspaces.status.
- CHECK "es arreglo" en recipients/cc/bcc/labels/references_header y oauth_credentials.scopes.
- FK compuesta mensaje→hilo del mismo buzón; caso→buzón del mismo espacio.
- Quitar clave duplicada case_messages(case_id,message_id).

**C · Renombres / fusiones con cambio de código** (sin migración todavía)
- C1: quitar tasks, reminders, notifications, audit_log de `admin_ops._WORKSPACE_CLEANUP_TABLES` y de `admin_purge_targets` (#181); quitar health-check de mail_accounts en system.py. Habilita 002.
- C2: eliminar communication_messages.provider y communication_threads.provider (leer de communication_accounts).
- C3: renombrar gmail_sync_jobs → mailbox_sync_jobs (sirve a Gmail, IMAP, Yahoo, Microsoft).
- C4: unificar notificaciones: hms_notifications + case_notifications → una tabla `notifications` con tipo.
- C5: communication_tasks.status a minúsculas; decidir idioma único de enums (sugerido: códigos en inglés, etiquetas en la UI en español).
- C6: profiles.email sincronizado desde auth.users (trigger) o eliminado.
- C7: correos de participantes/solicitantes como address_key normalizado; opcional `message_participants`.
- C8: attachments: confirmar con la cola Storage del #181 (bucket inexistente hoy) antes de decidir.

Orden de riesgo: 001 → 003 → (C1) → 002 → C2…C8.
