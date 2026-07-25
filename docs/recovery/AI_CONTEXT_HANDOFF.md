# HMS AI Assistant

# AI Context Handoff

---

# Propósito

Este documento permite que una nueva conversación con ChatGPT (u otro asistente de IA) recupere rápidamente el contexto del proyecto sin depender del historial de conversaciones.

Debe mantenerse actualizado después de cada cambio importante en la arquitectura o en las decisiones del proyecto.

---

# Resumen del Proyecto

**Nombre:** HMS AI Assistant

HMS AI Assistant es una plataforma SaaS orientada a la gestión inteligente del correo electrónico mediante Inteligencia Artificial.

El objetivo principal es convertir el correo electrónico en un centro inteligente de trabajo que permita:

- Detectar tareas automáticamente.
- Detectar pendientes.
- Detectar riesgos.
- Priorizar solicitudes.
- Automatizar procesos.
- Generar resúmenes ejecutivos.
- Integrarse con otros sistemas empresariales.

No es únicamente un lector de correos.

---

# Estado Actual

Actualmente el proyecto se encuentra consolidando su arquitectura.

Se decidió fortalecer primero la base del sistema antes de desarrollar funcionalidades avanzadas de Inteligencia Artificial.

El proyecto NO debe reiniciarse.

Debe evolucionar sobre la arquitectura existente.

---

# Stack Tecnológico

Frontend

- Next.js
- React
- TypeScript

Backend

- FastAPI
- Python

Base de Datos

- PostgreSQL
- Supabase

Autenticación

- Google OAuth 2.0

Proveedor de correo implementado

- Gmail

---

# Estado de los Componentes

| Componente | Estado |
|------------|--------|
| Frontend | Operativo |
| Backend | Operativo |
| Supabase | Operativo |
| Gmail | Funcional |
| OAuth | Parcial |
| IA | En diseño |
| Outlook | Pendiente |
| IMAP | Pendiente |

---

# Decisiones Importantes

- No reiniciar el proyecto.
- Mantener la arquitectura modular.
- Trabajar 100% en la nube.
- Utilizar Git como fuente oficial del código.
- Utilizar Supabase como base de datos principal.
- Diseñar el sistema para soportar múltiples proveedores de correo.
- Mantener la IA desacoplada del proveedor de correo.
- Documentar cada decisión importante.
- Crear checkpoints antes de cambios de alto impacto.

---

# Documentación Disponible

Antes de realizar cualquier cambio revisar:

- PROJECT_STATE.md
- CURRENT_ARCHITECTURE.md
- DECISIONS_AND_PENDING.md
- RESTORE_GUIDE.md
- ENVIRONMENT_VARIABLES.md
- CHECKPOINT_MANIFEST.md

---

# Prioridades Actuales

1. Persistencia de credenciales OAuth.
2. Arquitectura de conectores.
3. Gestión completa de usuarios.
4. Multi Workspace.
5. Refactorización del backend.
6. Base para el motor de Inteligencia Artificial.

---

# Reglas para cualquier IA que continúe este proyecto

1. Leer toda la documentación del directorio `docs/recovery/` antes de proponer cambios.

2. No sugerir reiniciar el proyecto si existe una alternativa de evolución.

3. Mantener la arquitectura modular.

4. No romper compatibilidad sin una justificación técnica.

5. Documentar cualquier cambio importante realizado.

6. Mantener sincronizada la documentación con el código.

7. Antes de modificar componentes críticos, recomendar la creación de un nuevo checkpoint.

---

# Cómo retomar el proyecto en una nueva conversación

Al iniciar una nueva conversación:

1. Compartir el contenido del directorio `docs/recovery/`.
2. Compartir la auditoría más reciente del proyecto.
3. Indicar la rama de trabajo actual.
4. Explicar brevemente el objetivo de la sesión.

Con esa información, la IA debería poder continuar el desarrollo sin perder el contexto.

---

# Última actualización

25 de julio de 2026