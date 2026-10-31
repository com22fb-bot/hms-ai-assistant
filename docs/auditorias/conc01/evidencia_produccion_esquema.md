# Evidencia estructural de producción (solo lectura)

Proyecto Supabase hms-ai-assistant (us-west-2, Postgres 17.6). Consultas SOLO sobre information_schema/pg_catalog vía MCP execute_sql, 31-oct-2026 ~13:40 CDMX. Sin datos de negocio, sin escrituras.

## Columnas (tipo; ! = NOT NULL; =d = default)

```
case_events | id:uuid!=d, workspace_id:uuid!, case_id:uuid!, message_id:uuid, event_type:text!, level:integer!=d, title:text!, description:text, actor_type:text!=d, actor_identifier:text, dedupe_key:text, metadata:jsonb!=d, created_at:timestamp with time zone!=d
case_messages | id:uuid!=d, case_id:uuid!, message_id:uuid!, relation_type:text!=d, is_primary:boolean!=d, sequence_number:integer, linked_at:timestamp with time zone!=d
case_notifications | id:uuid!=d, workspace_id:uuid!, case_id:uuid!, event_id:uuid, level:integer!=d, channel:text!=d, title:text!, body:text, delivered_at:timestamp with time zone, read_at:timestamp with time zone, metadata:jsonb!=d, created_at:timestamp with time zone!=d
case_participants | id:uuid!=d, case_id:uuid!, email:text!, display_name:text, participant_role:text!=d, message_count:integer!=d, first_seen_at:timestamp with time zone!=d, last_seen_at:timestamp with time zone!=d, metadata:jsonb!=d
communication_accounts | id:uuid!=d, workspace_id:uuid!, provider:text!, provider_account_id:text, email:text, phone:text, display_name:text, avatar_url:text, status:text=d, last_sync_at:timestamp with time zone, created_at:timestamp with time zone=d, updated_at:timestamp with time zone=d, connected_by_profile_id:uuid, address_key:text
communication_messages | id:uuid!=d, thread_id:uuid, account_id:uuid, provider:text, external_message_id:text, sender:text, recipients:jsonb, cc:jsonb, bcc:jsonb, subject:text, body_text:text, body_html:text, received_at:timestamp with time zone, has_attachments:boolean=d, ai_processed:boolean=d, created_at:timestamp with time zone=d, labels:jsonb!=d, is_unread:boolean!=d, snippet:text, normalized_subject:text, direction:text!=d, internet_message_id:text, in_reply_to:text, references_header:jsonb!=d, correlation_key:text, case_processed:boolean!=d, processed_at:timestamp with time zone, updated_at:timestamp with time zone!=d, triage_category:text!=d, actionability_score:integer, triage_reason:text, triaged_at:timestamp with time zone, classification_rule_id:uuid, push_notified_at:timestamp with time zone, brain_confidence:numeric, brain_signals:jsonb
intelligent_cases | id:uuid!=d, workspace_id:uuid!, account_id:uuid, primary_thread_id:uuid, title:text!, normalized_subject:text, case_type:text!=d, status:text!=d, priority:text!=d, risk_score:integer!=d, confidence:numeric!=d, summary:text, requested_action:text, requester_name:text, requester_email:text, current_owner_email:text, waiting_on:text!=d, opened_at:timestamp with time zone!=d, last_activity_at:timestamp with time zone!=d, due_at:timestamp with time zone, resolved_at:timestamp with time zone, closed_at:timestamp with time zone, source_count:integer!=d, reminder_count:integer!=d, metadata:jsonb!=d, created_at:timestamp with time zone!=d, updated_at:timestamp with time zone!=d, triage_category:text!=d, actionability_score:integer, triage_reason:text, triaged_at:timestamp with time zone, event_at:timestamp with time zone
organizational_patterns | id:uuid!=d, workspace_id:uuid!, pattern_type:text!, pattern_key:text!, pattern_value:jsonb!=d, occurrences:integer!=d, confidence:numeric!=d, first_seen_at:timestamp with time zone!=d, last_seen_at:timestamp with time zone!=d, updated_at:timestamp with time zone!=d
```

## Restricciones (con), índices (idx), triggers (trg), RLS habilitada/forzada (rls), políticas (pol), privilegios efectivos de service_role (priv), roles BYPASSRLS (role), función CONC-01 existente (fn), versión (ver)

```
con | case_events | case_events_case_id_fkey | f | FOREIGN KEY (case_id) REFERENCES intelligent_cases(id) ON DELETE CASCADE
con | case_events | case_events_level_check | c | CHECK (((level >= 0) AND (level <= 4)))
con | case_events | case_events_message_id_fkey | f | FOREIGN KEY (message_id) REFERENCES communication_messages(id) ON DELETE SET NULL
con | case_events | case_events_pkey | p | PRIMARY KEY (id)
con | case_events | case_events_workspace_id_fkey | f | FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
con | case_messages | case_messages_case_id_fkey | f | FOREIGN KEY (case_id) REFERENCES intelligent_cases(id) ON DELETE CASCADE
con | case_messages | case_messages_case_id_message_id_key | u | UNIQUE (case_id, message_id)
con | case_messages | case_messages_message_id_fkey | f | FOREIGN KEY (message_id) REFERENCES communication_messages(id) ON DELETE CASCADE
con | case_messages | case_messages_pkey | p | PRIMARY KEY (id)
con | case_notifications | case_notifications_case_id_fkey | f | FOREIGN KEY (case_id) REFERENCES intelligent_cases(id) ON DELETE CASCADE
con | case_notifications | case_notifications_event_id_fkey | f | FOREIGN KEY (event_id) REFERENCES case_events(id) ON DELETE SET NULL
con | case_notifications | case_notifications_level_check | c | CHECK (((level >= 0) AND (level <= 4)))
con | case_notifications | case_notifications_pkey | p | PRIMARY KEY (id)
con | case_notifications | case_notifications_workspace_id_fkey | f | FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
con | case_participants | case_participants_case_id_email_key | u | UNIQUE (case_id, email)
con | case_participants | case_participants_case_id_fkey | f | FOREIGN KEY (case_id) REFERENCES intelligent_cases(id) ON DELETE CASCADE
con | case_participants | case_participants_pkey | p | PRIMARY KEY (id)
con | communication_accounts | communication_accounts_connected_by_profile_id_fkey | f | FOREIGN KEY (connected_by_profile_id) REFERENCES profiles(id) ON DELETE SET NULL
con | communication_accounts | communication_accounts_pkey | p | PRIMARY KEY (id)
con | communication_accounts | communication_accounts_workspace_id_fkey | f | FOREIGN KEY (workspace_id) REFERENCES workspaces(id)
con | communication_messages | communication_messages_account_id_external_message_id_key | u | UNIQUE (account_id, external_message_id)
con | communication_messages | communication_messages_account_id_fkey | f | FOREIGN KEY (account_id) REFERENCES communication_accounts(id) ON DELETE CASCADE
con | communication_messages | communication_messages_classification_rule_id_fkey | f | FOREIGN KEY (classification_rule_id) REFERENCES message_classification_rules(id) ON DELETE SET NULL
con | communication_messages | communication_messages_direction_check | c | CHECK ((direction = ANY (ARRAY['inbound'::text, 'outbound'::text, 'draft'::text, 'system'::text])))
con | communication_messages | communication_messages_pkey | p | PRIMARY KEY (id)
con | communication_messages | communication_messages_thread_id_fkey | f | FOREIGN KEY (thread_id) REFERENCES communication_threads(id) ON DELETE CASCADE
con | communication_messages | communication_messages_triage_category_check | c | CHECK ((triage_category = ANY (ARRAY['unreviewed'::text, 'action_required'::text, 'waiting_external'::text, 'review'::text, 'notice'::text, 'informational'::text, 'automated'::text, 'promotional'::text, 'social'::text])))
con | intelligent_cases | intelligent_cases_account_id_fkey | f | FOREIGN KEY (account_id) REFERENCES communication_accounts(id) ON DELETE CASCADE
con | intelligent_cases | intelligent_cases_pkey | p | PRIMARY KEY (id)
con | intelligent_cases | intelligent_cases_primary_thread_id_fkey | f | FOREIGN KEY (primary_thread_id) REFERENCES communication_threads(id) ON DELETE SET NULL
con | intelligent_cases | intelligent_cases_priority_check | c | CHECK ((priority = ANY (ARRAY['low'::text, 'normal'::text, 'high'::text, 'critical'::text])))
con | intelligent_cases | intelligent_cases_reminder_count_check | c | CHECK ((reminder_count >= 0))
con | intelligent_cases | intelligent_cases_risk_score_check | c | CHECK (((risk_score >= 0) AND (risk_score <= 100)))
con | intelligent_cases | intelligent_cases_source_count_check | c | CHECK ((source_count >= 0))
con | intelligent_cases | intelligent_cases_status_check | c | CHECK ((status = ANY (ARRAY['new'::text, 'analyzing'::text, 'in_progress'::text, 'delegated'::text, 'waiting_internal'::text, 'waiting_external'::text, 'resolved'::text, 'closed'::text, 'archived'::text, 'scheduled'::text, 'no_action'::text, 'needs_review'::text])))
con | intelligent_cases | intelligent_cases_triage_category_check | c | CHECK ((triage_category = ANY (ARRAY['unreviewed'::text, 'action_required'::text, 'waiting_external'::text, 'review'::text, 'informational'::text, 'automated'::text, 'promotional'::text])))
con | intelligent_cases | intelligent_cases_waiting_on_check | c | CHECK ((waiting_on = ANY (ARRAY['internal'::text, 'external'::text, 'none'::text])))
con | intelligent_cases | intelligent_cases_workspace_id_fkey | f | FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
con | organizational_patterns | organizational_patterns_pkey | p | PRIMARY KEY (id)
con | organizational_patterns | organizational_patterns_workspace_id_fkey | f | FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
con | organizational_patterns | organizational_patterns_workspace_id_pattern_type_pattern_k_key | u | UNIQUE (workspace_id, pattern_type, pattern_key)
idx | case_events | case_events_pkey |  | CREATE UNIQUE INDEX case_events_pkey ON public.case_events USING btree (id)
idx | case_events | idx_case_events_case |  | CREATE INDEX idx_case_events_case ON public.case_events USING btree (case_id, created_at DESC)
idx | case_events | idx_case_events_dedupe |  | CREATE UNIQUE INDEX idx_case_events_dedupe ON public.case_events USING btree (case_id, dedupe_key) WHERE (dedupe_key IS NOT NULL)
idx | case_events | idx_case_events_message |  | CREATE INDEX idx_case_events_message ON public.case_events USING btree (message_id)
idx | case_events | idx_case_events_workspace_level |  | CREATE INDEX idx_case_events_workspace_level ON public.case_events USING btree (workspace_id, level, created_at DESC)
idx | case_messages | case_messages_case_id_message_id_key |  | CREATE UNIQUE INDEX case_messages_case_id_message_id_key ON public.case_messages USING btree (case_id, message_id)
idx | case_messages | case_messages_pkey |  | CREATE UNIQUE INDEX case_messages_pkey ON public.case_messages USING btree (id)
idx | case_messages | idx_case_messages_case |  | CREATE INDEX idx_case_messages_case ON public.case_messages USING btree (case_id, linked_at)
idx | case_messages | idx_case_messages_message_unique |  | CREATE UNIQUE INDEX idx_case_messages_message_unique ON public.case_messages USING btree (message_id)
idx | case_notifications | case_notifications_pkey |  | CREATE UNIQUE INDEX case_notifications_pkey ON public.case_notifications USING btree (id)
idx | case_notifications | idx_case_notifications_case |  | CREATE INDEX idx_case_notifications_case ON public.case_notifications USING btree (case_id)
idx | case_notifications | idx_case_notifications_event |  | CREATE INDEX idx_case_notifications_event ON public.case_notifications USING btree (event_id)
idx | case_notifications | idx_case_notifications_unread |  | CREATE INDEX idx_case_notifications_unread ON public.case_notifications USING btree (workspace_id, read_at, created_at DESC)
idx | case_participants | case_participants_case_id_email_key |  | CREATE UNIQUE INDEX case_participants_case_id_email_key ON public.case_participants USING btree (case_id, email)
idx | case_participants | case_participants_pkey |  | CREATE UNIQUE INDEX case_participants_pkey ON public.case_participants USING btree (id)
idx | case_participants | idx_case_participants_email |  | CREATE INDEX idx_case_participants_email ON public.case_participants USING btree (email)
idx | communication_messages | communication_messages_account_id_external_message_id_key |  | CREATE UNIQUE INDEX communication_messages_account_id_external_message_id_key ON public.communication_messages USING btree (account_id, external_message_id)
idx | communication_messages | communication_messages_account_triage_received_idx |  | CREATE INDEX communication_messages_account_triage_received_idx ON public.communication_messages USING btree (account_id, triage_category, received_at DESC)
idx | communication_messages | communication_messages_pkey |  | CREATE UNIQUE INDEX communication_messages_pkey ON public.communication_messages USING btree (id)
idx | communication_messages | idx_messages_account_received |  | CREATE INDEX idx_messages_account_received ON public.communication_messages USING btree (account_id, received_at DESC)
idx | communication_messages | idx_messages_account_triage |  | CREATE INDEX idx_messages_account_triage ON public.communication_messages USING btree (account_id, triage_category)
idx | communication_messages | idx_messages_account_unread |  | CREATE INDEX idx_messages_account_unread ON public.communication_messages USING btree (account_id, is_unread)
idx | communication_messages | idx_messages_case_processing |  | CREATE INDEX idx_messages_case_processing ON public.communication_messages USING btree (account_id, case_processed, received_at)
idx | communication_messages | idx_messages_internet_message_id |  | CREATE INDEX idx_messages_internet_message_id ON public.communication_messages USING btree (account_id, internet_message_id)
idx | communication_messages | idx_messages_normalized_subject |  | CREATE INDEX idx_messages_normalized_subject ON public.communication_messages USING btree (account_id, normalized_subject)
idx | communication_messages | idx_messages_received |  | CREATE INDEX idx_messages_received ON public.communication_messages USING btree (received_at DESC)
idx | communication_messages | idx_messages_thread_received |  | CREATE INDEX idx_messages_thread_received ON public.communication_messages USING btree (thread_id, received_at DESC)
idx | intelligent_cases | idx_cases_account_priority |  | CREATE INDEX idx_cases_account_priority ON public.intelligent_cases USING btree (account_id, priority, last_activity_at DESC)
idx | intelligent_cases | idx_cases_due |  | CREATE INDEX idx_cases_due ON public.intelligent_cases USING btree (due_at) WHERE (due_at IS NOT NULL)
idx | intelligent_cases | idx_cases_event |  | CREATE INDEX idx_cases_event ON public.intelligent_cases USING btree (event_at) WHERE (event_at IS NOT NULL)
idx | intelligent_cases | idx_cases_normalized_subject |  | CREATE INDEX idx_cases_normalized_subject ON public.intelligent_cases USING btree (account_id, normalized_subject)
idx | intelligent_cases | idx_cases_thread |  | CREATE INDEX idx_cases_thread ON public.intelligent_cases USING btree (account_id, primary_thread_id)
idx | intelligent_cases | idx_cases_workspace_status |  | CREATE INDEX idx_cases_workspace_status ON public.intelligent_cases USING btree (workspace_id, status, last_activity_at DESC)
idx | intelligent_cases | idx_intelligent_cases_account_triage_status |  | CREATE INDEX idx_intelligent_cases_account_triage_status ON public.intelligent_cases USING btree (account_id, triage_category, status)
idx | intelligent_cases | idx_intelligent_cases_primary_thread |  | CREATE INDEX idx_intelligent_cases_primary_thread ON public.intelligent_cases USING btree (primary_thread_id)
idx | intelligent_cases | intelligent_cases_pkey |  | CREATE UNIQUE INDEX intelligent_cases_pkey ON public.intelligent_cases USING btree (id)
idx | organizational_patterns | idx_organizational_patterns_lookup |  | CREATE INDEX idx_organizational_patterns_lookup ON public.organizational_patterns USING btree (workspace_id, pattern_type, occurrences DESC)
idx | organizational_patterns | organizational_patterns_pkey |  | CREATE UNIQUE INDEX organizational_patterns_pkey ON public.organizational_patterns USING btree (id)
idx | organizational_patterns | organizational_patterns_workspace_id_pattern_type_pattern_k_key |  | CREATE UNIQUE INDEX organizational_patterns_workspace_id_pattern_type_pattern_k_key ON public.organizational_patterns USING btree (workspace_id, pattern_type, pattern_key)
pol | communication_accounts | hms_accounts_select_member | SELECT | authenticated
priv | case_events | service_role |  | S,I,U,D
priv | case_messages | service_role |  | S,I,U,D
priv | case_notifications | service_role |  | S,I,U,D
priv | case_participants | service_role |  | S,I,U,D
priv | communication_accounts | service_role |  | S,I,U,D
priv | communication_messages | service_role |  | S,I,U,D
priv | intelligent_cases | service_role |  | S,I,U,D
priv | organizational_patterns | service_role |  | S,I,U,D
rls | case_events | true/false |  | 
rls | case_messages | true/false |  | 
rls | case_notifications | true/false |  | 
rls | case_participants | true/false |  | 
rls | communication_accounts | true/false |  | 
rls | communication_messages | true/false |  | 
rls | intelligent_cases | true/false |  | 
rls | organizational_patterns | true/false |  | 
role | anon | false |  | 
role | authenticated | false |  | 
role | postgres | true |  | 
role | service_role | true |  | 
trg | intelligent_cases | trg_intelligent_cases_updated | BEFORE UPDATE | EXECUTE FUNCTION set_updated_at()
trg | organizational_patterns | trg_organizational_patterns_updated | BEFORE UPDATE | EXECUTE FUNCTION set_updated_at()
ver | server | 17.6 |  | 
```

## Columnas completas de mensajes/casos/cuentas y set_updated_at()

```
cfg | set_updated_at | search_path=public
col | communication_accounts | address_key:text
col | communication_accounts | avatar_url:text
col | communication_accounts | connected_by_profile_id:uuid
col | communication_accounts | created_at:timestamp with time zone
col | communication_accounts | display_name:text
col | communication_accounts | email:text
col | communication_accounts | id:uuid!
col | communication_accounts | last_sync_at:timestamp with time zone
col | communication_accounts | phone:text
col | communication_accounts | provider:text!
col | communication_accounts | provider_account_id:text
col | communication_accounts | status:text
col | communication_accounts | updated_at:timestamp with time zone
col | communication_accounts | workspace_id:uuid!
col | communication_messages | account_id:uuid
col | communication_messages | actionability_score:integer
col | communication_messages | ai_processed:boolean
col | communication_messages | bcc:jsonb
col | communication_messages | body_html:text
col | communication_messages | body_text:text
col | communication_messages | brain_confidence:numeric
col | communication_messages | brain_signals:jsonb
col | communication_messages | case_processed:boolean!
col | communication_messages | cc:jsonb
col | communication_messages | classification_rule_id:uuid
col | communication_messages | correlation_key:text
col | communication_messages | created_at:timestamp with time zone
col | communication_messages | direction:text!
col | communication_messages | external_message_id:text
col | communication_messages | has_attachments:boolean
col | communication_messages | id:uuid!
col | communication_messages | in_reply_to:text
col | communication_messages | internet_message_id:text
col | communication_messages | is_unread:boolean!
col | communication_messages | labels:jsonb!
col | communication_messages | normalized_subject:text
col | communication_messages | processed_at:timestamp with time zone
col | communication_messages | provider:text
col | communication_messages | push_notified_at:timestamp with time zone
col | communication_messages | received_at:timestamp with time zone
col | communication_messages | recipients:jsonb
col | communication_messages | references_header:jsonb!
col | communication_messages | sender:text
col | communication_messages | snippet:text
col | communication_messages | subject:text
col | communication_messages | thread_id:uuid
col | communication_messages | triage_category:text!
col | communication_messages | triage_reason:text
col | communication_messages | triaged_at:timestamp with time zone
col | communication_messages | updated_at:timestamp with time zone!
col | intelligent_cases | account_id:uuid
col | intelligent_cases | actionability_score:integer
col | intelligent_cases | case_type:text!
col | intelligent_cases | closed_at:timestamp with time zone
col | intelligent_cases | confidence:numeric!
col | intelligent_cases | created_at:timestamp with time zone!
col | intelligent_cases | current_owner_email:text
col | intelligent_cases | due_at:timestamp with time zone
col | intelligent_cases | event_at:timestamp with time zone
col | intelligent_cases | id:uuid!
col | intelligent_cases | last_activity_at:timestamp with time zone!
col | intelligent_cases | metadata:jsonb!
col | intelligent_cases | normalized_subject:text
col | intelligent_cases | opened_at:timestamp with time zone!
col | intelligent_cases | primary_thread_id:uuid
col | intelligent_cases | priority:text!
col | intelligent_cases | reminder_count:integer!
col | intelligent_cases | requested_action:text
col | intelligent_cases | requester_email:text
col | intelligent_cases | requester_name:text
col | intelligent_cases | resolved_at:timestamp with time zone
col | intelligent_cases | risk_score:integer!
col | intelligent_cases | source_count:integer!
col | intelligent_cases | status:text!
col | intelligent_cases | summary:text
col | intelligent_cases | title:text!
col | intelligent_cases | triage_category:text!
col | intelligent_cases | triage_reason:text
col | intelligent_cases | triaged_at:timestamp with time zone
col | intelligent_cases | updated_at:timestamp with time zone!
col | intelligent_cases | waiting_on:text!
col | intelligent_cases | workspace_id:uuid!
fn | set_updated_at | CREATE OR REPLACE FUNCTION public.set_updated_at()  RETURNS trigger  LANGUAGE plpgsql  SET search_path TO 'public' AS $function$ begin     NEW.updated_at = now();     return NEW; end; $function$ 
```

## Hallazgos y ajustes
- BLOQUEANTE corregido: `communication_messages_triage_category_check` NO admite `classifying` ni `retry_pending` (estados de CONC-01 desde d2d0848). Sin ampliar el CHECK, toda reclamación falla con 23514. La migración lo amplía (NOT VALID + VALIDATE); prueba `test_prod_check_without_migration_rejects_claim`.
- `organizational_patterns` tiene UNIQUE (workspace_id, pattern_type, pattern_key): añadido al esquema local.
- Tipos uuid en thread_id/primary_thread_id con FK a communication_threads; FKs con ON DELETE; CHECKs; triggers `set_updated_at` (search_path=public) en intelligent_cases y organizational_patterns: replicados en `backend/tests/conc01/schema.sql`.
- RLS habilitada (no forzada) en las 8 tablas; única política: `hms_accounts_select_member` (SELECT, authenticated). service_role: BYPASSRLS=true y S/I/U/D en las 8 tablas; la RPC SECURITY INVOKER hereda exactamente eso.
- `conc01_commit_message` no existe en producción (fn: sin filas).

