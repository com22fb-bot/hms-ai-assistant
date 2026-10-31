-- PROPUESTA de modelo de datos del motor de casos. NO APLICAR.
-- Requiere autorización expresa de ASTRA/Héctor y un plan de migración revisado.
-- Todas las operaciones son ADITIVAS: no borran ni reescriben datos.

begin;

-- 1. Encabezados seleccionados (hoy se recuperan y se descartan).
create table if not exists public.message_headers (
  message_id uuid primary key references public.communication_messages(id) on delete cascade,
  list_unsubscribe text,
  list_id text,
  return_path text,
  authentication_results text,
  importance text,
  original_date text,          -- Date original con su zona horaria
  provider_internal_date timestamptz,
  created_at timestamptz not null default now()
);

-- 2. Adjuntos: la tabla existe (0 filas). Agregar texto extraído y hash.
alter table public.attachments
  add column if not exists sha256 text,
  add column if not exists extracted_text text,
  add column if not exists extraction_status text check (extraction_status in ('pending','ok','unsupported','error'));
create unique index if not exists attachments_message_sha_uq on public.attachments(message_id, sha256);

-- 3. Extracción estructurada con evidencia por campo.
create table if not exists public.event_extractions (
  id uuid primary key default gen_random_uuid(),
  message_id uuid not null references public.communication_messages(id) on delete cascade,
  workspace_id uuid not null,
  extractor_version text not null,
  event_type text not null,            -- taxonomía A–J
  taxonomy_area text not null,
  entity text,
  reference text,                      -- factura, pedido, transacción
  amount numeric(14,2),
  currency char(3),
  event_at timestamptz,
  due_at timestamptz,
  required_action text,
  responsible text,
  state text,
  confidence numeric(4,3) not null check (confidence between 0 and 1),
  fields_evidence jsonb not null default '{}'::jsonb,  -- {campo: {source:'body|attachment|header', ref, offset}}
  unknown_fields text[] not null default '{}',
  decision text not null check (decision in ('CREATE_CASE','UPDATE_CASE','REVIEW','INFORMATION_ONLY')),
  decision_reason text not null,
  created_at timestamptz not null default now(),
  unique (message_id, extractor_version)
);

-- 4. Casos: identidad del acontecimiento, importe y agregación.
alter table public.intelligent_cases
  add column if not exists event_identity_key text,
  add column if not exists taxonomy_area text,
  add column if not exists amount numeric(14,2),
  add column if not exists currency char(3),
  add column if not exists occurrence_count integer not null default 1,
  add column if not exists reopened_at timestamptz;

-- Un solo caso abierto por acontecimiento y usuario (evita duplicados).
create unique index if not exists intelligent_cases_open_identity_uq
  on public.intelligent_cases(workspace_id, event_identity_key)
  where event_identity_key is not null
    and status not in ('resolved','closed');

-- 5. Un mensaje se vincula una sola vez a un caso (ver CONC-01 / #214).
create unique index if not exists case_messages_case_msg_uq
  on public.case_messages(case_id, message_id);

commit;
