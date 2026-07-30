# Punto de restauración técnico — HMS AI Assistant

Fecha: Thu Jul 30 22:51:37 UTC 2026

Rama de trabajo: `sprint-4.1-ui`

Rama de respaldo: `backup/hms-communications-vision-20260730-225137`

Etiqueta: `restorepoint-hms-communications-20260730-225137`

Remoto: `https://github.com/com22fb-bot/hms-ai-assistant`

## Estado funcional

- Frontend con Next.js.
- Backend con FastAPI.
- Gmail OAuth funcionando.
- Selección de cuenta Google corregida.
- Consulta directa mediante `GET /gmail/messages`.
- Sincronización mediante `POST /gmail/sync`.
- Persistencia de mensajes en Supabase.
- Paginación de Gmail disponible.
- Límite actual de sincronización: 500 mensajes por ejecución.

## Tabla principal

`public.communication_messages`

Campos relevantes:

- thread_id
- account_id
- provider
- external_message_id
- sender
- recipients
- cc
- bcc
- subject
- body_text
- body_html
- received_at
- has_attachments
- ai_processed
- labels
- is_unread
- snippet

## Migración aplicada

`supabase/migrations/20260729_001_add_gmail_message_metadata.sql`

Resultado confirmado:

`Success. No rows returned.`

## Gmail Sync

`backend/app/services/gmail_sync.py` ya almacena:

- snippet
- labels
- is_unread

## Esquema

`backend/app/schemas/gmail.py` contiene los campos necesarios de GmailMessage.

## Siguiente paso pendiente

Crear `GET /gmail/stored-messages` para:

1. Obtener la cuenta Gmail activa.
2. Obtener account_id.
3. Consultar communication_messages.
4. Filtrar por account_id.
5. Ordenar por received_at DESC.
6. Aplicar paginación.
7. Responder con GmailMessagesResponse.
8. Mantener temporalmente /gmail/messages.
9. Cambiar después el frontend para leer desde Supabase.

## Cambio estratégico

Los mensajes almacenados alimentarán un monitor inteligente. No se construirá una réplica de la bandeja de entrada.

## Estado antes del commit

```text
A  .restorepoint_context
A  01_preparar_restorepoint.sh
M  backend/app/api/auth.py
M  backend/app/services/gmail_sync.py
A  docs/restorepoints/20260730-220609/VISION_ESTRATEGICA_HMS_COMMUNICATIONS_AI.md
A  docs/restorepoints/20260730-224121/README_RESTOREPOINT.md
A  docs/restorepoints/20260730-224121/VISION_ESTRATEGICA.md
A  docs/restorepoints/20260730-224505/README_RESTOREPOINT.md
A  docs/restorepoints/20260730-224505/VISION_ESTRATEGICA.md
A  docs/restorepoints/20260730-224920/REGISTRO_LITERAL_CAMBIO_DE_PERSPECTIVA.md
A  docs/restorepoints/20260730-224920/RESTOREPOINT_TECNICO.md
A  docs/restorepoints/20260730-224920/VALIDACIONES.log
A  docs/restorepoints/20260730-224920/VISION_ESTRATEGICA_HMS_COMMUNICATIONS_AI.md
A  docs/restorepoints/20260730-225028/REGISTRO_LITERAL_CAMBIO_DE_PERSPECTIVA.md
A  docs/restorepoints/20260730-225028/RESTOREPOINT_TECNICO.md
A  docs/restorepoints/20260730-225028/VALIDACIONES.log
A  docs/restorepoints/20260730-225028/VISION_ESTRATEGICA_HMS_COMMUNICATIONS_AI.md
A  docs/restorepoints/20260730-225113/REGISTRO_LITERAL_CAMBIO_DE_PERSPECTIVA.md
A  docs/restorepoints/20260730-225113/RESTOREPOINT_TECNICO.md
A  docs/restorepoints/20260730-225113/VALIDACIONES.log
A  docs/restorepoints/20260730-225113/VISION_ESTRATEGICA_HMS_COMMUNICATIONS_AI.md
M  frontend/.gitignore
M  frontend/hooks/useConnection.ts
M  frontend/next.config.ts
A  frontend/open-next.config.ts
M  frontend/package-lock.json
M  frontend/package.json
A  frontend/public/_headers
A  frontend/wrangler.jsonc
A  respaldo_maestro_hms_ai_assistant.sh
A  supabase/migrations/20260729_001_add_gmail_message_metadata.sql
?? docs/restorepoints/20260730-225137/
```
