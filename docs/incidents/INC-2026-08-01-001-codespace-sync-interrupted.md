# INC-2026-08-01-001 — Sincronización interrumpida por detención del Codespace

## Estado

**Resuelto**

## Severidad

Alta en el entorno de desarrollo.

## Resumen

El Codespace se detuvo mientras el navegador recorría el historial de Gmail en lotes de 50 mensajes. El frontend del puerto 3000 y el backend del puerto 8000 dejaron de responder, y el `next_page_token` vigente se perdió porque existía solamente en memoria de React.

## Impacto observado

- La interfaz dejó de responder con HTTP 502 y posteriormente HTTP 404.
- La sincronización se interrumpió después de aproximadamente 1,300 mensajes revisados.
- No se perdieron mensajes ya almacenados en Supabase.
- Quedaron 11 mensajes almacenados pendientes de convertirse en casos.

## Recuperación confirmada

- Servicios 3000 y 8000 reiniciados.
- OAuth de Google verificado como conectado.
- 1,410 mensajes almacenados.
- 1,399 mensajes procesados antes de la recuperación.
- 11 mensajes pendientes procesados manualmente.
- Resultado final: 1,410 procesados y 0 pendientes.
- Procesamiento de recuperación: 7 casos creados, 4 vinculados y 0 errores.

## Causa probable

Codespaces fue detenido mientras el flujo de sincronización dependía de procesos temporales y del estado de la pestaña del navegador.

## Corrección implementada en Sprint 4.7

- Tabla persistente `gmail_sync_jobs`.
- Persistencia del `next_page_token` después de cada lote.
- Un solo trabajo activo por cuenta.
- Reanudación al reiniciar FastAPI.
- Reintentos automáticos controlados.
- Detección de clics duplicados.
- Protección de duplicados mediante la llave existente `(account_id, external_message_id)`.
- Tabla persistente `system_incidents`.
- Middleware con `X-Request-ID` y registro automático de errores HTTP 5xx.
- El frontend consulta el estado del trabajo; ya no controla la paginación de Gmail.

## Limitación pendiente

Codespaces continúa siendo un entorno de desarrollo temporal. Mientras esté apagado, ningún proceso puede ejecutarse. La sincronización ahora conserva su progreso y se reanuda al volver a iniciar el backend; para ejecución continua será necesario desplegar el backend en infraestructura permanente.
