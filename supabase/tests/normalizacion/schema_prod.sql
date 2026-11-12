-- Esquema SOLO ESTRUCTURA de public (sin datos), generado de producción 23-oct-2026 vía pg_catalog (SELECT).
create extension if not exists citext; create extension if not exists pgcrypto;
create schema if not exists auth; create table if not exists auth.users (id uuid primary key default gen_random_uuid(), email text);
create table public.account_cleanup_runs (id uuid default gen_random_uuid() not null, ran_at timestamp with time zone not null, dry_run boolean not null, trial_due integer default 0 not null, lapsed_due integer default 0 not null, deleted integer default 0 not null, skipped_protected integer default 0 not null, reminders_mid integer default 0 not null, reminders_final integer default 0 not null, details jsonb default '{}'::jsonb not null);
create table public.account_plans (user_id uuid not null, plan_code text default 'trial'::text not null, status text default 'trialing'::text not null, trial_ends_at timestamp with time zone, period_ends_at timestamp with time zone, reminder_mid_sent_at timestamp with time zone, reminder_final_sent_at timestamp with time zone, last_manual_reminder_at timestamp with time zone, created_at timestamp with time zone not null, updated_at timestamp with time zone not null, is_test boolean default true not null, trial_started_at timestamp with time zone);
create table public.admin_allowlist (user_id uuid not null, created_at timestamp with time zone default now() not null);
create table public.admin_events (id uuid default gen_random_uuid() not null, occurred_at timestamp with time zone default now() not null, ended_at timestamp with time zone, source text default 'manual'::text not null, severity text default 'info'::text not null, title text not null, detail text default ''::text not null, status text default 'abierto'::text not null, created_by text default 'manual'::text not null, meta jsonb default '{}'::jsonb not null, external_id text, created_at timestamp with time zone default now() not null, updated_at timestamp with time zone default now() not null);
create table public.admin_expenses (id uuid default gen_random_uuid() not null, servicio text not null, plan text default ''::text not null, monto numeric(12,2) default 0 not null, moneda text default 'USD'::text not null, periodicidad text default 'mensual'::text not null, proximo_cobro date, notas text default ''::text not null, activo boolean default true not null, created_at timestamp with time zone default now() not null, updated_at timestamp with time zone default now() not null);
create table public.admin_settings (key text not null, value text not null, updated_at timestamp with time zone default now() not null);
create table public.ai_analysis (id uuid default gen_random_uuid() not null, message_id uuid, summary text, sentiment text, priority text, category text, requires_reply boolean default false, confidence numeric(5,2), entities jsonb default '{}'::jsonb, deadline timestamp with time zone, created_at timestamp with time zone default now());
create table public.alerts (id uuid default gen_random_uuid() not null, user_id uuid not null, task_id uuid, channel text not null, destination text, message_key text, payload jsonb default '{}'::jsonb not null, scheduled_at timestamp with time zone, sent_at timestamp with time zone, status text default 'PENDING'::text not null, created_at timestamp with time zone default now() not null);
create table public.attachments (id uuid default gen_random_uuid() not null, message_id uuid, filename text, mime_type text, size bigint, storage_path text, created_at timestamp with time zone default now());
create table public.audit_log (id uuid default gen_random_uuid() not null, user_id uuid, action text, entity text, entity_id text, old_values jsonb, new_values jsonb, ip text, created_at timestamp with time zone default now());
create table public.case_events (id uuid default gen_random_uuid() not null, workspace_id uuid not null, case_id uuid not null, message_id uuid, event_type text not null, level integer default 1 not null, title text not null, description text, actor_type text default 'system'::text not null, actor_identifier text, dedupe_key text, metadata jsonb default '{}'::jsonb not null, created_at timestamp with time zone default now() not null);
create table public.case_messages (id uuid default gen_random_uuid() not null, case_id uuid not null, message_id uuid not null, relation_type text default 'evidence'::text not null, is_primary boolean default false not null, sequence_number integer, linked_at timestamp with time zone default now() not null);
create table public.case_notifications (id uuid default gen_random_uuid() not null, workspace_id uuid not null, case_id uuid not null, event_id uuid, level integer default 2 not null, channel text default 'dashboard'::text not null, title text not null, body text, delivered_at timestamp with time zone, read_at timestamp with time zone, metadata jsonb default '{}'::jsonb not null, created_at timestamp with time zone default now() not null);
create table public.case_participants (id uuid default gen_random_uuid() not null, case_id uuid not null, email text not null, display_name text, participant_role text default 'participant'::text not null, message_count integer default 1 not null, first_seen_at timestamp with time zone default now() not null, last_seen_at timestamp with time zone default now() not null, metadata jsonb default '{}'::jsonb not null);
create table public.case_reclassification_runs (id uuid default gen_random_uuid() not null, workspace_id uuid not null, account_id uuid not null, status text default 'running'::text not null, dry_run boolean default false not null, total_cases integer default 0 not null, processed_cases integer default 0 not null, action_required integer default 0 not null, waiting_external integer default 0 not null, review integer default 0 not null, informational integer default 0 not null, automated integer default 0 not null, promotional integer default 0 not null, errors integer default 0 not null, last_error text, started_at timestamp with time zone default now() not null, completed_at timestamp with time zone, metadata jsonb default '{}'::jsonb not null, total_messages integer default 0 not null, processed_messages integer default 0 not null, removed_cases integer default 0 not null, without_case integer default 0 not null, current_batch integer default 0 not null, heartbeat_at timestamp with time zone, initiated_by uuid, classifier_version text, cancel_requested boolean default false not null);
create table public.case_triage_backups (id uuid default gen_random_uuid() not null, run_id uuid not null, case_id uuid not null, before_state jsonb not null, created_at timestamp with time zone default now() not null);
create table public.communication_accounts (id uuid default gen_random_uuid() not null, workspace_id uuid not null, provider text not null, provider_account_id text, email text, phone text, display_name text, avatar_url text, status text default 'active'::text, last_sync_at timestamp with time zone, created_at timestamp with time zone default now(), updated_at timestamp with time zone default now(), connected_by_profile_id uuid, address_key text);
create table public.communication_messages (id uuid default gen_random_uuid() not null, thread_id uuid, account_id uuid, provider text, external_message_id text, sender text, recipients jsonb, cc jsonb, bcc jsonb, subject text, body_text text, body_html text, received_at timestamp with time zone, has_attachments boolean default false, ai_processed boolean default false, created_at timestamp with time zone default now(), labels jsonb default '[]'::jsonb not null, is_unread boolean default false not null, snippet text, normalized_subject text, direction text default 'inbound'::text not null, internet_message_id text, in_reply_to text, references_header jsonb default '[]'::jsonb not null, correlation_key text, case_processed boolean default false not null, processed_at timestamp with time zone, updated_at timestamp with time zone default now() not null, triage_category text default 'unreviewed'::text not null, actionability_score integer, triage_reason text, triaged_at timestamp with time zone, classification_rule_id uuid, push_notified_at timestamp with time zone, brain_confidence numeric(5,4), brain_signals jsonb);
create table public.communication_tasks (id uuid default gen_random_uuid() not null, workspace_id uuid not null, message_id uuid not null, title text not null, description text, status text default 'OPEN'::text not null, priority text default 'MEDIUM'::text not null, due_at timestamp with time zone, assigned_to uuid, detected_by_ai boolean default true not null, created_at timestamp with time zone default now() not null, updated_at timestamp with time zone default now() not null);
create table public.communication_threads (id uuid default gen_random_uuid() not null, account_id uuid, provider text, external_thread_id text, subject text, participants text, last_message_at timestamp with time zone, created_at timestamp with time zone default now(), updated_at timestamp with time zone default now());
create table public.contact_messages (id uuid not null, name text default ''::text not null, email text not null, country text default ''::text not null, message text not null, language text default ''::text not null, subject text default ''::text not null, status text default 'nuevo'::text not null, ip_hash text, draft_body text, draft_error text, reply_body text, replied_at timestamp with time zone, created_at timestamp with time zone default now() not null, updated_at timestamp with time zone default now() not null);
create table public.donexto_alert_rules (profile_id uuid not null, rule_id text not null, workspace_id uuid, kind text not null, value text not null, enabled boolean default true not null, area text, updated_at timestamp with time zone default now() not null);
create table public.donexto_preferences (profile_id uuid not null, workspace_id uuid, preferences jsonb default '{}'::jsonb not null, updated_at timestamp with time zone default now() not null);
create table public.emails (id uuid default gen_random_uuid() not null, user_id uuid not null, mail_account_id uuid not null, provider_message_id text not null, provider_thread_id text, sender_name text, sender_email text, recipients jsonb default '[]'::jsonb not null, cc jsonb default '[]'::jsonb not null, subject text, body_text text, body_html text, received_at timestamp with time zone, folder text, is_read boolean default false not null, is_starred boolean default false not null, is_archived boolean default false not null, is_deleted boolean default false not null, has_attachments boolean default false not null, requires_response boolean, answered boolean, language text, ai_category text, ai_priority text, ai_summary text, ai_risk text, synchronized_at timestamp with time zone default now() not null);
create table public.gmail_sync_jobs (id uuid default gen_random_uuid() not null, workspace_id uuid not null, account_id uuid not null, status text default 'queued'::text not null, mode text default 'historical'::text not null, query text, next_page_token text, batch_size integer default 50 not null, process_cases boolean default true not null, pages_completed integer default 0 not null, messages_found integer default 0 not null, messages_inserted integer default 0 not null, duplicates integer default 0 not null, cases_processed integer default 0 not null, created_cases integer default 0 not null, linked_cases integer default 0 not null, errors integer default 0 not null, cancel_requested boolean default false not null, worker_id text, lease_expires_at timestamp with time zone, last_error text, metadata jsonb default '{}'::jsonb not null, started_at timestamp with time zone, heartbeat_at timestamp with time zone, completed_at timestamp with time zone, created_at timestamp with time zone not null, updated_at timestamp with time zone not null, retry_count integer default 0 not null, max_retries integer default 3 not null, selection_categories jsonb default '[]'::jsonb not null, unique_estimate bigint, import_cutoff_at timestamp with time zone);
create table public.hms_notifications (id uuid default gen_random_uuid() not null, workspace_id uuid not null, account_id uuid, profile_id uuid not null, notification_type text not null, title text not null, body text not null, url text default '/'::text not null, message_id uuid, case_id uuid, dedupe_key text not null, pushed_at timestamp with time zone, read_at timestamp with time zone, created_at timestamp with time zone default now() not null);
create table public.intelligent_cases (id uuid default gen_random_uuid() not null, workspace_id uuid not null, account_id uuid, primary_thread_id uuid, title text not null, normalized_subject text, case_type text default 'general'::text not null, status text default 'new'::text not null, priority text default 'normal'::text not null, risk_score integer default 20 not null, confidence numeric(5,4) default 0.6000 not null, summary text, requested_action text, requester_name text, requester_email text, current_owner_email text, waiting_on text default 'internal'::text not null, opened_at timestamp with time zone default now() not null, last_activity_at timestamp with time zone default now() not null, due_at timestamp with time zone, resolved_at timestamp with time zone, closed_at timestamp with time zone, source_count integer default 0 not null, reminder_count integer default 0 not null, metadata jsonb default '{}'::jsonb not null, created_at timestamp with time zone default now() not null, updated_at timestamp with time zone default now() not null, triage_category text default 'unreviewed'::text not null, actionability_score integer, triage_reason text, triaged_at timestamp with time zone, event_at timestamp with time zone);
create table public.mail_accounts (id uuid default gen_random_uuid() not null, user_id uuid not null, provider text not null, email_address text not null, display_name text, access_token_encrypted text, refresh_token_encrypted text, token_expires_at timestamp with time zone, last_sync_at timestamp with time zone, active boolean default true not null, created_at timestamp with time zone default now() not null);
create table public.message_classification_rules (id uuid default gen_random_uuid() not null, workspace_id uuid not null, account_id uuid not null, profile_id uuid not null, source_message_id uuid, name text not null, match_type text not null, match_value text not null, secondary_value text, target_category text not null, notify_push boolean default false not null, is_active boolean default true not null, priority integer default 100 not null, created_at timestamp with time zone default now() not null, updated_at timestamp with time zone default now() not null);
create table public.message_watch_matches (id uuid default gen_random_uuid() not null, rule_id uuid not null, message_id uuid not null, matched_at timestamp with time zone default now() not null, read_at timestamp with time zone, notified_at timestamp with time zone);
create table public.message_watch_rules (id uuid default gen_random_uuid() not null, workspace_id uuid not null, account_id uuid not null, profile_id uuid not null, source_message_id uuid not null, match_type text not null, sender_email text, normalized_subject text, display_label text, is_active boolean default true not null, notify_in_app boolean default true not null, notify_push boolean default true not null, created_at timestamp with time zone default now() not null, updated_at timestamp with time zone default now() not null);
create table public.notifications (id uuid default gen_random_uuid() not null, user_id uuid, channel text, title text, body text, delivered boolean default false, created_at timestamp with time zone default now());
create table public.oauth_credentials (id uuid default gen_random_uuid() not null, account_id uuid not null, access_token text, refresh_token text, expires_at timestamp with time zone, token_uri text, scopes jsonb default '[]'::jsonb, metadata jsonb default '{}'::jsonb, created_at timestamp with time zone default now(), updated_at timestamp with time zone default now());
create table public.oauth_states (state text not null, provider text not null, expires_at timestamp with time zone not null, created_at timestamp with time zone default now(), profile_id uuid, workspace_id uuid, return_to text);
create table public.ops_r3_operation (op_id uuid default gen_random_uuid() not null, script text not null, started_at timestamp with time zone default now() not null, finished_at timestamp with time zone, status text default 'running'::text not null);
create table public.ops_r3_rollback_report (op_id uuid not null, table_name text not null, row_id uuid not null, outcome text not null, detail text, at timestamp with time zone default now() not null);
create table public.ops_r3_rows (seq bigint not null, op_id uuid not null, table_name text not null, row_id uuid not null, action text not null, before_row jsonb, after_hash text);
create table public.organizational_patterns (id uuid default gen_random_uuid() not null, workspace_id uuid not null, pattern_type text not null, pattern_key text not null, pattern_value jsonb default '{}'::jsonb not null, occurrences integer default 1 not null, confidence numeric(5,4) default 0.5000 not null, first_seen_at timestamp with time zone default now() not null, last_seen_at timestamp with time zone default now() not null, updated_at timestamp with time zone default now() not null);
create table public.profiles (id uuid not null, full_name text, phone text, language text default 'es'::text not null, timezone text default 'America/Mexico_City'::text not null, created_at timestamp with time zone default now() not null, email citext, locale text default 'es-MX'::text not null, is_active boolean default true not null, metadata jsonb default '{}'::jsonb not null, updated_at timestamp with time zone not null, deleted_at timestamp with time zone);
create table public.push_delivery_log (id uuid default gen_random_uuid() not null, notification_id uuid, subscription_id uuid, status text not null, http_status integer, error_text text, created_at timestamp with time zone default now() not null);
create table public.push_subscriptions (id uuid default gen_random_uuid() not null, workspace_id uuid not null, profile_id uuid not null, endpoint text not null, p256dh text not null, auth_secret text not null, user_agent text, device_label text, is_active boolean default true not null, last_seen_at timestamp with time zone default now() not null, last_success_at timestamp with time zone, last_error text, created_at timestamp with time zone default now() not null, updated_at timestamp with time zone default now() not null, platform text, locale text);
create table public.reclassification_backup_rows (id uuid default gen_random_uuid() not null, run_id uuid not null, table_name text not null, source_id text, row_data jsonb not null, created_at timestamp with time zone default now() not null);
create table public.reminders (id uuid default gen_random_uuid() not null, task_id uuid, remind_at timestamp with time zone, sent boolean default false, created_at timestamp with time zone default now());
create table public.system_incidents (id uuid default gen_random_uuid() not null, incident_code text not null, workspace_id uuid, account_id uuid, sync_job_id uuid, occurred_at timestamp with time zone not null, environment text default 'development'::text not null, component text not null, severity text default 'medium'::text not null, event_type text not null, summary text not null, technical_detail text, http_status integer, request_id text, detected_by text default 'system'::text not null, status text default 'open'::text not null, resolved_at timestamp with time zone, resolution text, metadata jsonb default '{}'::jsonb not null, created_at timestamp with time zone not null, updated_at timestamp with time zone not null);
create table public.tasks (id uuid default gen_random_uuid() not null, user_id uuid not null, email_id uuid, title text not null, description text, task_type text, status text default 'OPEN'::text not null, priority text default 'MEDIUM'::text not null, due_at timestamp with time zone, assigned_to text, detected_by_ai boolean default false not null, completed_at timestamp with time zone, created_at timestamp with time zone default now() not null, message_id uuid);
create table public.user_workspaces (id uuid default gen_random_uuid() not null, workspace_id uuid not null, user_id uuid not null, role text default 'user'::text not null, created_at timestamp with time zone default now());
create table public.users (id uuid default gen_random_uuid() not null, email text not null, full_name text, password_hash text, status text default 'active'::text, created_at timestamp with time zone default now(), updated_at timestamp with time zone default now());
create table public.workspace_members (id uuid default gen_random_uuid() not null, workspace_id uuid not null, profile_id uuid not null, role text default 'viewer'::text not null, status text default 'active'::text not null, joined_at timestamp with time zone, created_at timestamp with time zone not null, updated_at timestamp with time zone not null, deleted_at timestamp with time zone);
create table public.workspaces (id uuid default gen_random_uuid() not null, name text not null, slug text, status text default 'active'::text not null, created_at timestamp with time zone default now() not null, updated_at timestamp with time zone default now() not null, owner_profile_id uuid);
alter table public.account_cleanup_runs add constraint account_cleanup_runs_pkey PRIMARY KEY (id);
alter table public.account_plans add constraint account_plans_pkey PRIMARY KEY (user_id);
alter table public.admin_allowlist add constraint admin_allowlist_pkey PRIMARY KEY (user_id);
alter table public.admin_events add constraint admin_events_external_id_key UNIQUE (external_id);
alter table public.admin_events add constraint admin_events_pkey PRIMARY KEY (id);
alter table public.admin_expenses add constraint admin_expenses_pkey PRIMARY KEY (id);
alter table public.admin_settings add constraint admin_settings_pkey PRIMARY KEY (key);
alter table public.ai_analysis add constraint ai_analysis_pkey PRIMARY KEY (id);
alter table public.ai_analysis add constraint ai_analysis_message_id_key UNIQUE (message_id);
alter table public.alerts add constraint alerts_pkey PRIMARY KEY (id);
alter table public.attachments add constraint attachments_pkey PRIMARY KEY (id);
alter table public.audit_log add constraint audit_log_pkey PRIMARY KEY (id);
alter table public.case_events add constraint case_events_pkey PRIMARY KEY (id);
alter table public.case_messages add constraint case_messages_case_id_message_id_key UNIQUE (case_id, message_id);
alter table public.case_messages add constraint case_messages_pkey PRIMARY KEY (id);
alter table public.case_notifications add constraint case_notifications_pkey PRIMARY KEY (id);
alter table public.case_participants add constraint case_participants_case_id_email_key UNIQUE (case_id, email);
alter table public.case_participants add constraint case_participants_pkey PRIMARY KEY (id);
alter table public.case_reclassification_runs add constraint case_reclassification_runs_pkey PRIMARY KEY (id);
alter table public.case_triage_backups add constraint case_triage_backups_run_id_case_id_key UNIQUE (run_id, case_id);
alter table public.case_triage_backups add constraint case_triage_backups_pkey PRIMARY KEY (id);
alter table public.communication_accounts add constraint communication_accounts_pkey PRIMARY KEY (id);
alter table public.communication_messages add constraint communication_messages_account_id_external_message_id_key UNIQUE (account_id, external_message_id);
alter table public.communication_messages add constraint communication_messages_pkey PRIMARY KEY (id);
alter table public.communication_tasks add constraint communication_tasks_pkey PRIMARY KEY (id);
alter table public.communication_threads add constraint communication_threads_pkey PRIMARY KEY (id);
alter table public.communication_threads add constraint communication_threads_account_id_external_thread_id_key UNIQUE (account_id, external_thread_id);
alter table public.contact_messages add constraint contact_messages_pkey PRIMARY KEY (id);
alter table public.donexto_alert_rules add constraint donexto_alert_rules_pkey PRIMARY KEY (profile_id, rule_id);
alter table public.donexto_preferences add constraint donexto_preferences_pkey PRIMARY KEY (profile_id);
alter table public.emails add constraint emails_pkey PRIMARY KEY (id);
alter table public.emails add constraint emails_mail_account_id_provider_message_id_key UNIQUE (mail_account_id, provider_message_id);
alter table public.gmail_sync_jobs add constraint gmail_sync_jobs_pkey PRIMARY KEY (id);
alter table public.hms_notifications add constraint hms_notifications_pkey PRIMARY KEY (id);
alter table public.hms_notifications add constraint hms_notifications_profile_id_dedupe_key_key UNIQUE (profile_id, dedupe_key);
alter table public.intelligent_cases add constraint intelligent_cases_pkey PRIMARY KEY (id);
alter table public.mail_accounts add constraint mail_accounts_pkey PRIMARY KEY (id);
alter table public.mail_accounts add constraint mail_accounts_user_id_email_address_key UNIQUE (user_id, email_address);
alter table public.message_classification_rules add constraint message_classification_rules_pkey PRIMARY KEY (id);
alter table public.message_watch_matches add constraint message_watch_matches_rule_id_message_id_key UNIQUE (rule_id, message_id);
alter table public.message_watch_matches add constraint message_watch_matches_pkey PRIMARY KEY (id);
alter table public.message_watch_rules add constraint message_watch_rules_profile_id_source_message_id_key UNIQUE (profile_id, source_message_id);
alter table public.message_watch_rules add constraint message_watch_rules_pkey PRIMARY KEY (id);
alter table public.notifications add constraint notifications_pkey PRIMARY KEY (id);
alter table public.oauth_credentials add constraint oauth_credentials_pkey PRIMARY KEY (id);
alter table public.oauth_credentials add constraint oauth_credentials_account_id_key UNIQUE (account_id);
alter table public.oauth_states add constraint oauth_states_pkey PRIMARY KEY (state);
alter table public.ops_r3_operation add constraint ops_r3_operation_pkey PRIMARY KEY (op_id);
alter table public.ops_r3_rows add constraint ops_r3_rows_pkey PRIMARY KEY (seq);
alter table public.organizational_patterns add constraint organizational_patterns_pkey PRIMARY KEY (id);
alter table public.organizational_patterns add constraint organizational_patterns_workspace_id_pattern_type_pattern_k_key UNIQUE (workspace_id, pattern_type, pattern_key);
alter table public.profiles add constraint profiles_pkey PRIMARY KEY (id);
alter table public.push_delivery_log add constraint push_delivery_log_pkey PRIMARY KEY (id);
alter table public.push_subscriptions add constraint push_subscriptions_profile_id_endpoint_key UNIQUE (profile_id, endpoint);
alter table public.push_subscriptions add constraint push_subscriptions_pkey PRIMARY KEY (id);
alter table public.reclassification_backup_rows add constraint reclassification_backup_rows_pkey PRIMARY KEY (id);
alter table public.reminders add constraint reminders_pkey PRIMARY KEY (id);
alter table public.system_incidents add constraint system_incidents_pkey PRIMARY KEY (id);
alter table public.system_incidents add constraint system_incidents_incident_code_key UNIQUE (incident_code);
alter table public.tasks add constraint tasks_pkey PRIMARY KEY (id);
alter table public.user_workspaces add constraint user_workspaces_pkey PRIMARY KEY (id);
alter table public.user_workspaces add constraint user_workspaces_workspace_id_user_id_key UNIQUE (workspace_id, user_id);
alter table public.users add constraint users_email_key UNIQUE (email);
alter table public.users add constraint users_pkey PRIMARY KEY (id);
alter table public.workspace_members add constraint uq_hms_workspace_members UNIQUE (workspace_id, profile_id);
alter table public.workspace_members add constraint workspace_members_pkey PRIMARY KEY (id);
alter table public.workspaces add constraint workspaces_pkey PRIMARY KEY (id);
alter table public.workspaces add constraint workspaces_slug_key UNIQUE (slug);
alter table public.account_plans add constraint account_plans_plan_code_check CHECK ((plan_code = ANY (ARRAY['trial'::text, 'monthly'::text, 'annual'::text])));
alter table public.account_plans add constraint account_plans_status_check CHECK ((status = ANY (ARRAY['trialing'::text, 'active'::text, 'lapsed'::text, 'canceled'::text])));
alter table public.admin_events add constraint admin_events_status_check CHECK ((status = ANY (ARRAY['abierto'::text, 'resuelto'::text])));
alter table public.admin_events add constraint admin_events_severity_check CHECK ((severity = ANY (ARRAY['info'::text, 'aviso'::text, 'grave'::text, 'critico'::text])));
alter table public.admin_events add constraint admin_events_source_check CHECK ((source = ANY (ARRAY['railway'::text, 'cloudflare'::text, 'supabase'::text, 'github'::text, 'backup'::text, 'monitor'::text, 'deploy'::text, 'manual'::text])));
alter table public.admin_events add constraint admin_events_title_check CHECK (((length(title) >= 1) AND (length(title) <= 200)));
alter table public.admin_expenses add constraint admin_expenses_moneda_check CHECK ((moneda = ANY (ARRAY['USD'::text, 'MXN'::text])));
alter table public.admin_expenses add constraint admin_expenses_periodicidad_check CHECK ((periodicidad = ANY (ARRAY['mensual'::text, 'anual'::text, 'unico'::text])));
alter table public.case_events add constraint case_events_level_check CHECK (((level >= 0) AND (level <= 4)));
alter table public.case_notifications add constraint case_notifications_level_check CHECK (((level >= 0) AND (level <= 4)));
alter table public.case_reclassification_runs add constraint case_reclassification_runs_status_check CHECK ((status = ANY (ARRAY['running'::text, 'completed'::text, 'failed'::text, 'cancelled'::text])));
alter table public.communication_messages add constraint communication_messages_triage_category_check CHECK ((triage_category = ANY (ARRAY['unreviewed'::text, 'action_required'::text, 'waiting_external'::text, 'review'::text, 'notice'::text, 'informational'::text, 'automated'::text, 'promotional'::text, 'social'::text])));
alter table public.communication_messages add constraint communication_messages_direction_check CHECK ((direction = ANY (ARRAY['inbound'::text, 'outbound'::text, 'draft'::text, 'system'::text])));
alter table public.communication_tasks add constraint communication_tasks_status_check CHECK ((status = ANY (ARRAY['OPEN'::text, 'IN_PROGRESS'::text, 'COMPLETED'::text, 'CANCELLED'::text])));
alter table public.communication_tasks add constraint communication_tasks_priority_check CHECK ((priority = ANY (ARRAY['LOW'::text, 'MEDIUM'::text, 'HIGH'::text, 'CRITICAL'::text])));
alter table public.contact_messages add constraint contact_messages_status_check CHECK ((status = ANY (ARRAY['nuevo'::text, 'borrador listo'::text, 'enviando'::text, 'respondido'::text, 'archivado'::text])));
alter table public.donexto_alert_rules add constraint donexto_alert_rules_kind_check CHECK ((kind = ANY (ARRAY['sender'::text, 'case_type'::text, 'subject'::text, 'concept'::text])));
alter table public.donexto_preferences add constraint chk_donexto_preferences_object CHECK ((jsonb_typeof(preferences) = 'object'::text));
alter table public.gmail_sync_jobs add constraint chk_gmail_sync_jobs_batch_size CHECK (((batch_size >= 1) AND (batch_size <= 100)));
alter table public.gmail_sync_jobs add constraint chk_gmail_sync_jobs_status CHECK ((status = ANY (ARRAY['queued'::text, 'running'::text, 'paused'::text, 'interrupted'::text, 'completed'::text, 'failed'::text, 'cancelled'::text])));
alter table public.gmail_sync_jobs add constraint chk_gmail_sync_jobs_mode CHECK ((mode = ANY (ARRAY['historical'::text, 'incremental'::text, 'custom'::text])));
alter table public.gmail_sync_jobs add constraint chk_gmail_sync_jobs_retry_controls CHECK (((retry_count >= 0) AND ((max_retries >= 0) AND (max_retries <= 10))));
alter table public.gmail_sync_jobs add constraint chk_gmail_sync_jobs_nonnegative CHECK (((pages_completed >= 0) AND (messages_found >= 0) AND (messages_inserted >= 0) AND (duplicates >= 0) AND (cases_processed >= 0) AND (created_cases >= 0) AND (linked_cases >= 0) AND (errors >= 0)));
alter table public.gmail_sync_jobs add constraint chk_gmail_sync_jobs_metadata_object CHECK ((jsonb_typeof(metadata) = 'object'::text));
alter table public.intelligent_cases add constraint intelligent_cases_triage_category_check CHECK ((triage_category = ANY (ARRAY['unreviewed'::text, 'action_required'::text, 'waiting_external'::text, 'review'::text, 'informational'::text, 'automated'::text, 'promotional'::text])));
alter table public.intelligent_cases add constraint intelligent_cases_status_check CHECK ((status = ANY (ARRAY['new'::text, 'analyzing'::text, 'in_progress'::text, 'delegated'::text, 'waiting_internal'::text, 'waiting_external'::text, 'resolved'::text, 'closed'::text, 'archived'::text, 'scheduled'::text, 'no_action'::text, 'needs_review'::text])));
alter table public.intelligent_cases add constraint intelligent_cases_priority_check CHECK ((priority = ANY (ARRAY['low'::text, 'normal'::text, 'high'::text, 'critical'::text])));
alter table public.intelligent_cases add constraint intelligent_cases_waiting_on_check CHECK ((waiting_on = ANY (ARRAY['internal'::text, 'external'::text, 'none'::text])));
alter table public.intelligent_cases add constraint intelligent_cases_reminder_count_check CHECK ((reminder_count >= 0));
alter table public.intelligent_cases add constraint intelligent_cases_source_count_check CHECK ((source_count >= 0));
alter table public.intelligent_cases add constraint intelligent_cases_risk_score_check CHECK (((risk_score >= 0) AND (risk_score <= 100)));
alter table public.message_classification_rules add constraint message_classification_rules_match_type_check CHECK ((match_type = ANY (ARRAY['sender'::text, 'sender_domain'::text, 'subject_contains'::text, 'body_contains'::text, 'sender_subject'::text])));
alter table public.message_classification_rules add constraint message_classification_rules_target_category_check CHECK ((target_category = ANY (ARRAY['action_required'::text, 'review'::text, 'notice'::text, 'social'::text, 'promotional'::text, 'automated'::text, 'informational'::text])));
alter table public.message_watch_rules add constraint message_watch_rules_match_type_check CHECK ((match_type = ANY (ARRAY['sender'::text, 'subject'::text, 'sender_subject'::text])));
alter table public.ops_r3_rows add constraint ops_r3_rows_action_check CHECK ((action = ANY (ARRAY['insert'::text, 'update'::text, 'delete'::text])));
alter table public.push_delivery_log add constraint push_delivery_log_status_check CHECK ((status = ANY (ARRAY['sent'::text, 'failed'::text, 'expired'::text, 'skipped'::text])));
alter table public.system_incidents add constraint chk_system_incidents_severity CHECK ((severity = ANY (ARRAY['info'::text, 'low'::text, 'medium'::text, 'high'::text, 'critical'::text])));
alter table public.system_incidents add constraint chk_system_incidents_metadata_object CHECK ((jsonb_typeof(metadata) = 'object'::text));
alter table public.system_incidents add constraint chk_system_incidents_http_status CHECK (((http_status IS NULL) OR ((http_status >= 100) AND (http_status <= 599))));
alter table public.system_incidents add constraint chk_system_incidents_status CHECK ((status = ANY (ARRAY['open'::text, 'investigating'::text, 'resolved'::text, 'ignored'::text])));
alter table public.system_incidents add constraint chk_system_incidents_resolution CHECK (((status <> 'resolved'::text) OR (resolved_at IS NOT NULL)));
alter table public.workspace_members add constraint chk_hms_workspace_member_status CHECK ((status = ANY (ARRAY['invited'::text, 'active'::text, 'suspended'::text, 'removed'::text])));
alter table public.workspace_members add constraint chk_hms_workspace_member_role CHECK ((role = ANY (ARRAY['owner'::text, 'admin'::text, 'manager'::text, 'operator'::text, 'viewer'::text, 'auditor'::text])));
alter table public.account_plans add constraint account_plans_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
alter table public.admin_allowlist add constraint admin_allowlist_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
alter table public.ai_analysis add constraint ai_analysis_message_id_fkey FOREIGN KEY (message_id) REFERENCES communication_messages(id) ON DELETE CASCADE;
alter table public.alerts add constraint alerts_task_id_fkey FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE;
alter table public.alerts add constraint alerts_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
alter table public.attachments add constraint attachments_message_id_fkey FOREIGN KEY (message_id) REFERENCES communication_messages(id) ON DELETE CASCADE;
alter table public.case_events add constraint case_events_message_id_fkey FOREIGN KEY (message_id) REFERENCES communication_messages(id) ON DELETE SET NULL;
alter table public.case_events add constraint case_events_case_id_fkey FOREIGN KEY (case_id) REFERENCES intelligent_cases(id) ON DELETE CASCADE;
alter table public.case_events add constraint case_events_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE;
alter table public.case_messages add constraint case_messages_case_id_fkey FOREIGN KEY (case_id) REFERENCES intelligent_cases(id) ON DELETE CASCADE;
alter table public.case_messages add constraint case_messages_message_id_fkey FOREIGN KEY (message_id) REFERENCES communication_messages(id) ON DELETE CASCADE;
alter table public.case_notifications add constraint case_notifications_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE;
alter table public.case_notifications add constraint case_notifications_event_id_fkey FOREIGN KEY (event_id) REFERENCES case_events(id) ON DELETE SET NULL;
alter table public.case_notifications add constraint case_notifications_case_id_fkey FOREIGN KEY (case_id) REFERENCES intelligent_cases(id) ON DELETE CASCADE;
alter table public.case_participants add constraint case_participants_case_id_fkey FOREIGN KEY (case_id) REFERENCES intelligent_cases(id) ON DELETE CASCADE;
alter table public.case_reclassification_runs add constraint case_reclassification_runs_account_id_fkey FOREIGN KEY (account_id) REFERENCES communication_accounts(id) ON DELETE CASCADE;
alter table public.case_reclassification_runs add constraint case_reclassification_runs_initiated_by_fkey FOREIGN KEY (initiated_by) REFERENCES profiles(id) ON DELETE SET NULL;
alter table public.case_reclassification_runs add constraint case_reclassification_runs_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE;
alter table public.case_triage_backups add constraint case_triage_backups_case_id_fkey FOREIGN KEY (case_id) REFERENCES intelligent_cases(id) ON DELETE CASCADE;
alter table public.case_triage_backups add constraint case_triage_backups_run_id_fkey FOREIGN KEY (run_id) REFERENCES case_reclassification_runs(id) ON DELETE CASCADE;
alter table public.communication_accounts add constraint communication_accounts_connected_by_profile_id_fkey FOREIGN KEY (connected_by_profile_id) REFERENCES profiles(id) ON DELETE SET NULL;
alter table public.communication_accounts add constraint communication_accounts_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES workspaces(id);
alter table public.communication_messages add constraint communication_messages_classification_rule_id_fkey FOREIGN KEY (classification_rule_id) REFERENCES message_classification_rules(id) ON DELETE SET NULL;
alter table public.communication_messages add constraint communication_messages_thread_id_fkey FOREIGN KEY (thread_id) REFERENCES communication_threads(id) ON DELETE CASCADE;
alter table public.communication_messages add constraint communication_messages_account_id_fkey FOREIGN KEY (account_id) REFERENCES communication_accounts(id) ON DELETE CASCADE;
alter table public.communication_tasks add constraint communication_tasks_message_id_fkey FOREIGN KEY (message_id) REFERENCES communication_messages(id) ON DELETE CASCADE;
alter table public.communication_threads add constraint communication_threads_account_id_fkey FOREIGN KEY (account_id) REFERENCES communication_accounts(id) ON DELETE CASCADE;
alter table public.donexto_alert_rules add constraint donexto_alert_rules_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE SET NULL;
alter table public.donexto_alert_rules add constraint donexto_alert_rules_profile_id_fkey FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE;
alter table public.donexto_preferences add constraint donexto_preferences_profile_id_fkey FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE;
alter table public.donexto_preferences add constraint donexto_preferences_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE SET NULL;
alter table public.emails add constraint emails_mail_account_id_fkey FOREIGN KEY (mail_account_id) REFERENCES mail_accounts(id) ON DELETE CASCADE;
alter table public.emails add constraint emails_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
alter table public.gmail_sync_jobs add constraint gmail_sync_jobs_account_id_fkey FOREIGN KEY (account_id) REFERENCES communication_accounts(id) ON DELETE CASCADE;
alter table public.gmail_sync_jobs add constraint gmail_sync_jobs_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE;
alter table public.hms_notifications add constraint hms_notifications_account_id_fkey FOREIGN KEY (account_id) REFERENCES communication_accounts(id) ON DELETE CASCADE;
alter table public.hms_notifications add constraint hms_notifications_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE;
alter table public.hms_notifications add constraint hms_notifications_profile_id_fkey FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE;
alter table public.hms_notifications add constraint hms_notifications_message_id_fkey FOREIGN KEY (message_id) REFERENCES communication_messages(id) ON DELETE CASCADE;
alter table public.hms_notifications add constraint hms_notifications_case_id_fkey FOREIGN KEY (case_id) REFERENCES intelligent_cases(id) ON DELETE CASCADE;
alter table public.intelligent_cases add constraint intelligent_cases_primary_thread_id_fkey FOREIGN KEY (primary_thread_id) REFERENCES communication_threads(id) ON DELETE SET NULL;
alter table public.intelligent_cases add constraint intelligent_cases_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE;
alter table public.intelligent_cases add constraint intelligent_cases_account_id_fkey FOREIGN KEY (account_id) REFERENCES communication_accounts(id) ON DELETE CASCADE;
alter table public.mail_accounts add constraint mail_accounts_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
alter table public.message_classification_rules add constraint message_classification_rules_profile_id_fkey FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE;
alter table public.message_classification_rules add constraint message_classification_rules_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE;
alter table public.message_classification_rules add constraint message_classification_rules_account_id_fkey FOREIGN KEY (account_id) REFERENCES communication_accounts(id) ON DELETE CASCADE;
alter table public.message_classification_rules add constraint message_classification_rules_source_message_id_fkey FOREIGN KEY (source_message_id) REFERENCES communication_messages(id) ON DELETE SET NULL;
alter table public.message_watch_matches add constraint message_watch_matches_rule_id_fkey FOREIGN KEY (rule_id) REFERENCES message_watch_rules(id) ON DELETE CASCADE;
alter table public.message_watch_matches add constraint message_watch_matches_message_id_fkey FOREIGN KEY (message_id) REFERENCES communication_messages(id) ON DELETE CASCADE;
alter table public.message_watch_rules add constraint message_watch_rules_account_id_fkey FOREIGN KEY (account_id) REFERENCES communication_accounts(id) ON DELETE CASCADE;
alter table public.message_watch_rules add constraint message_watch_rules_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE;
alter table public.message_watch_rules add constraint message_watch_rules_source_message_id_fkey FOREIGN KEY (source_message_id) REFERENCES communication_messages(id) ON DELETE CASCADE;
alter table public.message_watch_rules add constraint message_watch_rules_profile_id_fkey FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE;
alter table public.notifications add constraint notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);
alter table public.oauth_credentials add constraint oauth_credentials_account_id_fkey FOREIGN KEY (account_id) REFERENCES communication_accounts(id) ON DELETE CASCADE;
alter table public.oauth_states add constraint oauth_states_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE;
alter table public.oauth_states add constraint oauth_states_profile_id_fkey FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE;
alter table public.ops_r3_rows add constraint ops_r3_rows_op_id_fkey FOREIGN KEY (op_id) REFERENCES ops_r3_operation(op_id);
alter table public.organizational_patterns add constraint organizational_patterns_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE;
alter table public.profiles add constraint profiles_id_fkey FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE;
alter table public.push_delivery_log add constraint push_delivery_log_notification_id_fkey FOREIGN KEY (notification_id) REFERENCES hms_notifications(id) ON DELETE CASCADE;
alter table public.push_delivery_log add constraint push_delivery_log_subscription_id_fkey FOREIGN KEY (subscription_id) REFERENCES push_subscriptions(id) ON DELETE SET NULL;
alter table public.push_subscriptions add constraint push_subscriptions_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE;
alter table public.push_subscriptions add constraint push_subscriptions_profile_id_fkey FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE;
alter table public.reclassification_backup_rows add constraint reclassification_backup_rows_run_id_fkey FOREIGN KEY (run_id) REFERENCES case_reclassification_runs(id) ON DELETE CASCADE;
alter table public.reminders add constraint reminders_task_id_fkey FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE;
alter table public.system_incidents add constraint system_incidents_account_id_fkey FOREIGN KEY (account_id) REFERENCES communication_accounts(id) ON DELETE SET NULL;
alter table public.system_incidents add constraint system_incidents_sync_job_id_fkey FOREIGN KEY (sync_job_id) REFERENCES gmail_sync_jobs(id) ON DELETE SET NULL;
alter table public.system_incidents add constraint system_incidents_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE SET NULL;
alter table public.tasks add constraint tasks_message_id_fkey FOREIGN KEY (message_id) REFERENCES communication_messages(id) ON DELETE CASCADE;
alter table public.tasks add constraint tasks_email_id_fkey FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE SET NULL;
alter table public.tasks add constraint tasks_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
alter table public.user_workspaces add constraint user_workspaces_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE;
alter table public.user_workspaces add constraint user_workspaces_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
alter table public.workspace_members add constraint workspace_members_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE;
alter table public.workspace_members add constraint workspace_members_profile_id_fkey FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE;
alter table public.workspaces add constraint workspaces_owner_profile_id_fkey FOREIGN KEY (owner_profile_id) REFERENCES profiles(id) ON DELETE SET NULL;
CREATE INDEX admin_events_source_idx ON public.admin_events USING btree (source, occurred_at DESC);
CREATE INDEX admin_events_occurred_idx ON public.admin_events USING btree (occurred_at DESC);
CREATE INDEX idx_attachments_message ON public.attachments USING btree (message_id);
CREATE INDEX idx_case_events_message ON public.case_events USING btree (message_id);
CREATE UNIQUE INDEX idx_case_events_dedupe ON public.case_events USING btree (case_id, dedupe_key) WHERE (dedupe_key IS NOT NULL);
CREATE INDEX idx_case_events_case ON public.case_events USING btree (case_id, created_at DESC);
CREATE INDEX idx_case_events_workspace_level ON public.case_events USING btree (workspace_id, level, created_at DESC);
CREATE UNIQUE INDEX idx_case_messages_message_unique ON public.case_messages USING btree (message_id);
CREATE INDEX idx_case_messages_case ON public.case_messages USING btree (case_id, linked_at);
CREATE INDEX idx_case_notifications_case ON public.case_notifications USING btree (case_id);
CREATE INDEX idx_case_notifications_event ON public.case_notifications USING btree (event_id);
CREATE INDEX idx_case_notifications_unread ON public.case_notifications USING btree (workspace_id, read_at, created_at DESC);
CREATE INDEX idx_case_participants_email ON public.case_participants USING btree (email);
CREATE UNIQUE INDEX uq_case_reclassification_active_account ON public.case_reclassification_runs USING btree (account_id) WHERE (status = 'running'::text);
CREATE INDEX idx_accounts_workspace ON public.communication_accounts USING btree (workspace_id);
CREATE INDEX idx_hms_accounts_connected_by_profile ON public.communication_accounts USING btree (connected_by_profile_id) WHERE (connected_by_profile_id IS NOT NULL);
CREATE UNIQUE INDEX ux_comm_accounts_live_address ON public.communication_accounts USING btree (provider, address_key) WHERE (status = ANY (ARRAY['active'::text, 'needs_reauth'::text]));
CREATE INDEX idx_hms_accounts_workspace_provider ON public.communication_accounts USING btree (workspace_id, provider, status);
CREATE INDEX idx_accounts_provider ON public.communication_accounts USING btree (provider);
CREATE INDEX idx_messages_thread_received ON public.communication_messages USING btree (thread_id, received_at DESC);
CREATE INDEX idx_messages_received ON public.communication_messages USING btree (received_at DESC);
CREATE INDEX idx_messages_account_received ON public.communication_messages USING btree (account_id, received_at DESC);
CREATE INDEX idx_messages_account_unread ON public.communication_messages USING btree (account_id, is_unread);
CREATE INDEX idx_messages_case_processing ON public.communication_messages USING btree (account_id, case_processed, received_at);
CREATE INDEX idx_messages_normalized_subject ON public.communication_messages USING btree (account_id, normalized_subject);
CREATE INDEX idx_messages_internet_message_id ON public.communication_messages USING btree (account_id, internet_message_id);
CREATE INDEX idx_messages_account_triage ON public.communication_messages USING btree (account_id, triage_category);
CREATE INDEX communication_messages_account_triage_received_idx ON public.communication_messages USING btree (account_id, triage_category, received_at DESC);
CREATE INDEX idx_communication_tasks_message_id ON public.communication_tasks USING btree (message_id);
CREATE INDEX idx_communication_tasks_status ON public.communication_tasks USING btree (status);
CREATE INDEX idx_communication_tasks_workspace_id ON public.communication_tasks USING btree (workspace_id);
CREATE INDEX idx_contact_messages_created ON public.contact_messages USING btree (created_at DESC);
CREATE INDEX idx_contact_messages_status ON public.contact_messages USING btree (status, created_at DESC);
CREATE INDEX idx_donexto_alert_rules_profile ON public.donexto_alert_rules USING btree (profile_id, enabled);
CREATE INDEX idx_emails_user_id ON public.emails USING btree (user_id);
CREATE INDEX idx_emails_received_at ON public.emails USING btree (received_at DESC);
CREATE INDEX idx_gmail_sync_jobs_status_heartbeat ON public.gmail_sync_jobs USING btree (status, heartbeat_at);
CREATE UNIQUE INDEX uq_gmail_sync_jobs_active_account ON public.gmail_sync_jobs USING btree (account_id) WHERE (status = ANY (ARRAY['queued'::text, 'running'::text, 'paused'::text, 'interrupted'::text]));
CREATE INDEX idx_gmail_sync_jobs_workspace_created ON public.gmail_sync_jobs USING btree (workspace_id, created_at DESC);
CREATE INDEX idx_gmail_sync_jobs_account_created ON public.gmail_sync_jobs USING btree (account_id, created_at DESC);
CREATE INDEX idx_hms_notifications_message ON public.hms_notifications USING btree (message_id);
CREATE INDEX idx_hms_notifications_workspace ON public.hms_notifications USING btree (workspace_id);
CREATE INDEX idx_hms_notifications_case ON public.hms_notifications USING btree (case_id);
CREATE INDEX idx_hms_notifications_profile_unread ON public.hms_notifications USING btree (profile_id, read_at, created_at DESC);
CREATE INDEX idx_cases_normalized_subject ON public.intelligent_cases USING btree (account_id, normalized_subject);
CREATE INDEX idx_cases_due ON public.intelligent_cases USING btree (due_at) WHERE (due_at IS NOT NULL);
CREATE INDEX idx_intelligent_cases_account_triage_status ON public.intelligent_cases USING btree (account_id, triage_category, status);
CREATE INDEX idx_intelligent_cases_primary_thread ON public.intelligent_cases USING btree (primary_thread_id);
CREATE INDEX idx_cases_event ON public.intelligent_cases USING btree (event_at) WHERE (event_at IS NOT NULL);
CREATE INDEX idx_cases_workspace_status ON public.intelligent_cases USING btree (workspace_id, status, last_activity_at DESC);
CREATE INDEX idx_cases_account_priority ON public.intelligent_cases USING btree (account_id, priority, last_activity_at DESC);
CREATE INDEX idx_cases_thread ON public.intelligent_cases USING btree (account_id, primary_thread_id);
CREATE INDEX idx_mail_accounts_user_id ON public.mail_accounts USING btree (user_id);
CREATE INDEX idx_message_classification_rules_account ON public.message_classification_rules USING btree (account_id, is_active, priority, created_at);
CREATE INDEX idx_message_watch_matches_unread ON public.message_watch_matches USING btree (rule_id, read_at, matched_at DESC);
CREATE INDEX idx_message_watch_rules_active ON public.message_watch_rules USING btree (account_id, profile_id, is_active);
CREATE INDEX idx_message_watch_rules_subject ON public.message_watch_rules USING btree (account_id, normalized_subject) WHERE (is_active = true);
CREATE INDEX idx_message_watch_rules_sender ON public.message_watch_rules USING btree (account_id, sender_email) WHERE (is_active = true);
CREATE INDEX idx_hms_oauth_states_profile ON public.oauth_states USING btree (profile_id, expires_at) WHERE (profile_id IS NOT NULL);
CREATE INDEX idx_hms_oauth_states_workspace ON public.oauth_states USING btree (workspace_id, provider, expires_at);
CREATE INDEX ops_r3_rows_op ON public.ops_r3_rows USING btree (op_id, seq);
CREATE INDEX idx_organizational_patterns_lookup ON public.organizational_patterns USING btree (workspace_id, pattern_type, occurrences DESC);
CREATE UNIQUE INDEX uq_hms_profiles_email_active ON public.profiles USING btree (lower((email)::text)) WHERE ((email IS NOT NULL) AND (deleted_at IS NULL));
CREATE INDEX idx_push_subscriptions_profile_active ON public.push_subscriptions USING btree (profile_id, is_active);
CREATE INDEX idx_reclassification_backup_run ON public.reclassification_backup_rows USING btree (run_id, table_name);
CREATE INDEX idx_system_incidents_sync_job ON public.system_incidents USING btree (sync_job_id) WHERE (sync_job_id IS NOT NULL);
CREATE INDEX idx_system_incidents_status_severity ON public.system_incidents USING btree (status, severity, occurred_at DESC);
CREATE INDEX idx_system_incidents_workspace_occurred ON public.system_incidents USING btree (workspace_id, occurred_at DESC);
CREATE INDEX idx_tasks_message_id ON public.tasks USING btree (message_id);
CREATE INDEX idx_tasks_status ON public.tasks USING btree (status);
CREATE INDEX idx_tasks_user_id ON public.tasks USING btree (user_id);
CREATE INDEX idx_user_workspaces_user ON public.user_workspaces USING btree (user_id);
CREATE INDEX idx_hms_workspace_members_profile_active ON public.workspace_members USING btree (profile_id, status) WHERE (deleted_at IS NULL);
CREATE INDEX idx_hms_workspaces_owner_profile ON public.workspaces USING btree (owner_profile_id) WHERE (owner_profile_id IS NOT NULL);
CREATE OR REPLACE FUNCTION public.ops_r3_log(p_op uuid, p_table text, p_id uuid, p_action text, p_before jsonb)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'public'
AS $function$
begin
  insert into public.ops_r3_rows (op_id, table_name, row_id, action, before_row, after_hash)
  values (p_op, p_table, p_id, p_action, p_before,
          case when p_action = 'delete' then null else public.ops_r3_row_hash(p_table, p_id) end);
end $function$
;
CREATE OR REPLACE FUNCTION public.ops_r3_rollback(p_op uuid)
 RETURNS TABLE(outcome text, n bigint)
 LANGUAGE plpgsql
 SET search_path TO 'public'
AS $function$
declare r record; cur text; cols text; collist text; st text;
begin
  -- Concurrencia: un solo rollback a la vez (candado de transacción global) y
  -- la operación se bloquea FOR UPDATE. Una segunda corrida, simultánea o
  -- posterior, espera y luego solo devuelve el reporte: no revierte dos veces.
  perform pg_advisory_xact_lock(hashtextextended('ops_r3_rollback', 0));
  select o.status into st from public.ops_r3_operation o where o.op_id = p_op for update;
  if not found then
    raise exception 'ops_r3_rollback: operación inexistente';
  end if;
  if st = 'rolled_back' then
    return query select x.outcome, count(*) from public.ops_r3_rollback_report x where x.op_id = p_op group by 1;
    return;
  end if;
  set local lock_timeout = '10s';
  -- restaurar valores exactos (incluido updated_at) sin que el trigger los pise
  alter table public.communication_accounts disable trigger user;
  alter table public.oauth_credentials disable trigger user;
  alter table public.communication_messages disable trigger user;
  for r in select * from public.ops_r3_rows where op_id = p_op order by seq desc loop
    -- bloquea la fila objetivo: nadie la cambia entre la comparación y la restauración
    execute format('select 1 from public.%I where id = $1 for update', r.table_name) using r.row_id;
    if r.action = 'insert' then
      cur := public.ops_r3_row_hash(r.table_name, r.row_id);
      if cur is null then
        insert into public.ops_r3_rollback_report values (p_op, r.table_name, r.row_id, 'already_gone', null);
      elsif cur <> r.after_hash then
        insert into public.ops_r3_rollback_report values (p_op, r.table_name, r.row_id, 'skipped_changed',
          'la fila cambió después de la operación');
      elsif public.ops_r3_has_children(r.table_name, r.row_id) then
        insert into public.ops_r3_rollback_report values (p_op, r.table_name, r.row_id, 'skipped_dependents',
          'tiene filas hijas posteriores');
      else
        execute format('delete from public.%I where id = $1', r.table_name) using r.row_id;
        insert into public.ops_r3_rollback_report values (p_op, r.table_name, r.row_id, 'reverted', null);
      end if;
    elsif r.action = 'update' then
      cur := public.ops_r3_row_hash(r.table_name, r.row_id);
      if cur is distinct from r.after_hash then
        insert into public.ops_r3_rollback_report values (p_op, r.table_name, r.row_id, 'skipped_changed',
          'actividad posterior: no se restaura');
      else
        select string_agg(format('%I = src.%I', column_name, column_name), ', ') into cols
        from information_schema.columns
        where table_schema = 'public' and table_name = r.table_name and column_name <> 'id'
          and is_generated = 'NEVER';
        execute format('update public.%I t set %s from jsonb_populate_record(null::public.%I, $1) src where t.id = $2',
                       r.table_name, cols, r.table_name) using r.before_row, r.row_id;
        insert into public.ops_r3_rollback_report values (p_op, r.table_name, r.row_id, 'reverted', null);
      end if;
    elsif r.action = 'delete' then
      if public.ops_r3_row_hash(r.table_name, r.row_id) is not null
         or (r.table_name = 'oauth_credentials' and exists (
               select 1 from public.oauth_credentials o where o.account_id = (r.before_row->>'account_id')::uuid)) then
        insert into public.ops_r3_rollback_report values (p_op, r.table_name, r.row_id, 'skipped_conflict',
          'ya existe una fila nueva (p. ej. reconexión)');
      else
        select string_agg(format('%I', column_name), ', ' order by ordinal_position) into collist
        from information_schema.columns
        where table_schema = 'public' and table_name = r.table_name and is_generated = 'NEVER';
        execute format('insert into public.%I (%s) select %s from jsonb_populate_record(null::public.%I, $1)',
                       r.table_name, collist, collist, r.table_name) using r.before_row;
        insert into public.ops_r3_rollback_report values (p_op, r.table_name, r.row_id, 'reverted', null);
      end if;
    end if;
  end loop;
  alter table public.communication_accounts enable trigger user;
  alter table public.oauth_credentials enable trigger user;
  alter table public.communication_messages enable trigger user;
  update public.ops_r3_operation set status = 'rolled_back', finished_at = now() where op_id = p_op;
  return query select x.outcome, count(*) from public.ops_r3_rollback_report x where x.op_id = p_op group by 1;
end $function$
;
