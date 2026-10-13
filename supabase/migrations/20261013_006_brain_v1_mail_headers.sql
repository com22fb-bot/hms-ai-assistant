-- Cerebro v1 · Adenda 1.3 punto 5 (BRAIN_V1_ENABLED). Migración ADITIVA, NO APLICADA.
-- Guarda List-Unsubscribe, List-Unsubscribe-Post, List-Id y etiquetas del proveedor al importar.
-- Con la bandera apagada el código no escribe esta columna.
-- Rollback: alter table public.communication_messages drop column if exists mail_headers;
begin;
alter table public.communication_messages add column if not exists mail_headers jsonb;
commit;
