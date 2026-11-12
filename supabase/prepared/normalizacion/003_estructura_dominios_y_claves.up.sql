-- 003 · B: dominios (CHECK), integridad entre claves (FK compuestas) y un índice redundante.
-- PREPARADA, NO APLICADA. Requiere confirmación de Héctor (lista B). Sin cambios de código.
-- Producción hoy: communication_accounts/messages/threads/intelligent_cases = 0 filas, así que validar es instantáneo.
begin;
-- DKNF / dominios: valores permitidos explícitos (hoy texto libre)
alter table public.communication_accounts add constraint ck_comm_accounts_status
  check (status in ('active','needs_reauth','inactive','disconnected','superseded','paused','error'));
alter table public.communication_accounts add constraint ck_comm_accounts_provider
  check (provider in ('google','gmail','gmail_imap','microsoft','hotmail','outlook','yahoo','icloud','imap','other'));
alter table public.communication_threads add constraint ck_comm_threads_provider
  check (provider is null or provider in ('google','gmail','gmail_imap','microsoft','hotmail','outlook','yahoo','icloud','imap','other'));
alter table public.communication_messages add constraint ck_comm_messages_provider
  check (provider is null or provider in ('google','gmail','gmail_imap','microsoft','hotmail','outlook','yahoo','icloud','imap','other'));
alter table public.workspaces add constraint ck_workspaces_status
  check (status in ('active','inactive','suspended','deleted','archived'));
-- 1NF de dominio: las listas JSONB deben ser arreglos (no objetos ni escalares)
alter table public.communication_messages add constraint ck_comm_messages_lists_are_arrays check (
  (recipients is null or jsonb_typeof(recipients)='array') and (cc is null or jsonb_typeof(cc)='array') and
  (bcc is null or jsonb_typeof(bcc)='array') and (labels is null or jsonb_typeof(labels)='array') and
  (references_header is null or jsonb_typeof(references_header)='array'));
alter table public.oauth_credentials add constraint ck_oauth_scopes_array
  check (scopes is null or jsonb_typeof(scopes)='array');
-- 3NF/EKNF: el hilo de un mensaje debe pertenecer al MISMO buzón; el buzón de un caso al MISMO espacio
alter table public.communication_threads add constraint uq_comm_threads_id_account unique (id, account_id);
alter table public.communication_messages add constraint fk_comm_messages_thread_same_account
  foreign key (thread_id, account_id) references public.communication_threads (id, account_id) on delete cascade;
alter table public.communication_accounts add constraint uq_comm_accounts_id_workspace unique (id, workspace_id);
alter table public.intelligent_cases add constraint fk_cases_account_same_workspace
  foreign key (account_id, workspace_id) references public.communication_accounts (id, workspace_id) on delete cascade;
-- Índice redundante: message_id ya es único por sí solo
alter table public.case_messages drop constraint if exists case_messages_case_id_message_id_key;
drop index if exists public.case_messages_case_id_message_id_key;
commit;
