# Sprint 4.3 — Implementación del Intelligent Case Engine

## Componentes incluidos

1. Message Repository persistente.
2. Correlation Engine determinista.
3. Intelligent Case Engine.
4. Event Engine.
5. Notificaciones por eventos.
6. Aprendizaje organizacional inicial.
7. APIs de casos, mensajes y dashboard.
8. Dashboard web orientado a Casos Inteligentes.
9. Pruebas del normalizador de asuntos.

## Principios preservados

- Los mensajes son evidencia.
- Los casos representan trabajo.
- Un mensaje enviado no cierra automáticamente un caso.
- El sistema notifica eventos de negocio.
- La sincronización y el razonamiento permanecen separados.
- Toda evolución posterior debe conservar trazabilidad.

## Flujo

Gmail → Supabase → Message Repository → Correlation Engine →
Case Engine → Event Engine → Notifications → Dashboard.

## Endpoints

- `GET /messages/stored`
- `GET /messages/stored/{message_id}`
- `POST /cases/process`
- `GET /cases`
- `GET /cases/dashboard`
- `GET /cases/notifications`
- `GET /cases/{case_id}`
- `PATCH /cases/{case_id}`
- `POST /gmail/sync?process_cases=true`
