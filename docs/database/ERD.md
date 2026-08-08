# HMS AI Assistant - Entity Relationship Diagram (ERD)

> Estado: Draft v1.0
> Sprint: 0 - Arquitectura
> Objetivo: Definir el modelo relacional principal de la plataforma.

---

# Arquitectura General

```text
Profile
    │
    ├──────────────┐
    │              │
    ▼              ▼
Workspace      Registered Device
    │
    ▼
Workspace Member
    │
    ├─────────────────────────────┐
    │                             │
    ▼                             ▼
Mail Account                 Workspace Role
    │
    ▼
Mail Account Access
    │
    ▼
Email
    │
    ├───────────────┬───────────────┐
    ▼               ▼               ▼
Attachment        Task           AI Analysis
    │                               │
    └───────────────┬───────────────┘
                    ▼
                 Alerts
```

---

# Entidades

## profiles

Representa una persona autenticada.

Relaciones:

- 1:N Workspaces (propietario)
- N:M Workspace Members
- 1:N Registered Devices

---

## workspaces

Representa un entorno de trabajo.

Tipos:

- personal
- organization

Relaciones:

- 1:N Workspace Members
- 1:N Mail Accounts

---

## workspace_members

Relaciona personas con workspaces.

Roles iniciales:

- owner
- admin
- manager
- operator
- viewer
- auditor

---

## mail_accounts

Representa una conexión con un proveedor de correo.

Ejemplos:

- Gmail
- Yahoo
- Outlook
- Microsoft 365

Pertenece a:

- Workspace

No pertenece directamente al usuario.

---

## mail_account_access

Define qué miembros pueden utilizar un buzón.

Permisos:

- read
- send
- assign
- archive
- delete
- export

---

## emails

Representa un mensaje sincronizado.

Incluye:

- metadata
- contenido
- estado
- etiquetas IA

---

## attachments

Archivos adjuntos.

---

## tasks

Tareas creadas manualmente o detectadas por IA.

---

## ai_analysis

Resultado estructurado generado por IA.

Puede contener:

- resumen
- prioridad
- riesgo
- sentimiento
- intención
- entidades detectadas
- fechas
- montos
- nivel de confianza

---

## alerts

Recordatorios y notificaciones.

---

## registered_devices

Dispositivos autorizados.

---

## audit_events

Registro completo de acciones importantes.

Nunca deberá modificarse.

---

# Relaciones principales

Profile
1 ---- N Workspace Member

Workspace
1 ---- N Workspace Member

Workspace
1 ---- N Mail Account

Mail Account
1 ---- N Email

Mail Account
1 ---- N Mail Account Access

Workspace Member
1 ---- N Mail Account Access

Email
1 ---- N Attachment

Email
1 ---- N Task

Email
1 ---- 1 AI Analysis

Task
1 ---- N Alert

Profile
1 ---- N Registered Device

Workspace
1 ---- N Audit Event

---

# Principios

- Multi Tenant.
- Workspace First.
- Shared Mailboxes.
- Least Privilege.
- Row Level Security.
- Audit First.
- Cloud Native.
- Provider Agnostic.