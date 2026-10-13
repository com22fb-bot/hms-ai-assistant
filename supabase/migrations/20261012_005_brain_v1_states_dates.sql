-- Cerebro v1 · Etapa 1 (BRAIN_V1_ENABLED). Migración ADITIVA: no borra ni reescribe datos.
-- NO APLICADA en producción. Aplicar antes de encender BRAIN_V1_ENABLED; con la bandera
-- apagada el código nunca usa estas columnas ni estados.
--  C9: estados nuevos scheduled (programado), no_action (sin acción), needs_review (requiere revisión).
--      El CHECK se reemplaza por un superconjunto: todas las filas válidas hoy siguen siendo válidas.
--  C2: intelligent_cases.event_at separado de due_at (que ya existe).
--  C8: confianza y señales por mensaje.
-- Rollback (solo si ninguna fila usa los estados nuevos):
--   alter table public.intelligent_cases drop constraint intelligent_cases_status_check;
--   alter table public.intelligent_cases add constraint intelligent_cases_status_check check (status = any (array[
--     'new','analyzing','in_progress','delegated','waiting_internal','waiting_external','resolved','closed','archived']));
--   alter table public.intelligent_cases drop column if exists event_at;
--   alter table public.communication_messages drop column if exists brain_confidence, drop column if exists brain_signals;
begin;
alter table public.intelligent_cases drop constraint if exists intelligent_cases_status_check;
alter table public.intelligent_cases add constraint intelligent_cases_status_check check (status = any (array[
  'new','analyzing','in_progress','delegated','waiting_internal','waiting_external','resolved','closed','archived',
  'scheduled','no_action','needs_review']));
alter table public.intelligent_cases add column if not exists event_at timestamptz;
create index if not exists idx_cases_event on public.intelligent_cases (event_at) where event_at is not null;
alter table public.communication_messages add column if not exists brain_confidence numeric(5,4);
alter table public.communication_messages add column if not exists brain_signals jsonb;
commit;
