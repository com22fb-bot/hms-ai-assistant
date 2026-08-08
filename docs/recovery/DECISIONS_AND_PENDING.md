# HMS AI Assistant

# Decisiones de Arquitectura y Pendientes

---

# Objetivo del documento

Este documento registra las decisiones importantes tomadas durante el desarrollo del proyecto.

Su propósito es evitar volver a discutir decisiones ya aprobadas y servir como referencia para cualquier desarrollador o sesión futura de ChatGPT.

---

# Decisiones Confirmadas

## Arquitectura General

✓ El proyecto continuará sobre la arquitectura actual.

✓ No se reiniciará el desarrollo.

✓ Se evolucionará la arquitectura existente.

---

## Plataforma

✓ Desarrollo 100% en la nube.

✓ No depender de entornos locales para el desarrollo principal.

✓ El repositorio Git será la fuente oficial del código.

---

## Backend

✓ FastAPI como framework principal.

✓ Arquitectura modular.

✓ Separación entre API, Servicios, Base de Datos y Esquemas.

✓ Reducir progresivamente la responsabilidad de `main.py`.

---

## Frontend

✓ Next.js.

✓ TypeScript.

✓ React.

✓ Dashboard modular.

---

## Base de Datos

✓ PostgreSQL mediante Supabase.

✓ Uso de migraciones versionadas.

✓ Evitar cambios manuales directamente sobre producción.

---

## Autenticación

✓ Google OAuth 2.0.

✓ Persistencia futura de tokens en la base de datos.

✓ Preparar el sistema para múltiples proveedores de autenticación.

---

## Correos Electrónicos

✓ Gmail será el primer proveedor soportado.

✓ La arquitectura deberá permitir agregar Outlook e IMAP sin modificar el núcleo del sistema.

---

## Inteligencia Artificial

✓ La IA será un servicio independiente.

✓ No deberá depender del proveedor de correo.

✓ La IA analizará el contenido una sola vez y generará múltiples resultados reutilizables.

---

## Workspaces

✓ El sistema será multiempresa.

✓ Cada Workspace será independiente.

✓ Los usuarios pertenecerán a uno o varios Workspaces.

---

## Seguridad

✓ No almacenar secretos en Git.

✓ Uso de archivos `.env`.

✓ Variables sensibles únicamente en el servidor.

---

# Pendientes Técnicos

## Alta prioridad

- Persistencia de OAuth.
- Gestión completa de usuarios.
- Gestión de Workspaces.
- Arquitectura de conectores.
- Refactorización de `main.py`.

---

## Prioridad media

- Outlook.
- IMAP.
- Automatizaciones.
- Notificaciones.
- Auditoría.

---

## Prioridad futura

- WhatsApp.
- Microsoft Teams.
- Slack.
- ERP.
- CRM.
- Motor avanzado de IA.
- Reportes ejecutivos.

---

# Reglas del Proyecto

1. No reiniciar el proyecto sin una justificación técnica.

2. Mantener la arquitectura modular.

3. Documentar cualquier cambio importante.

4. Crear un checkpoint antes de modificaciones de alto impacto.

5. Mantener compatibilidad con migraciones anteriores.

6. No almacenar información sensible en el repositorio.

7. Toda funcionalidad nueva deberá quedar documentada.

---

# Última actualización

25 de julio de 2026