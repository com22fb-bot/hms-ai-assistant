# HMS AI Assistant

# Arquitectura Actual del Sistema

---

# Visión General

HMS AI Assistant está diseñado como una plataforma SaaS modular para la administración inteligente del correo electrónico mediante Inteligencia Artificial.

La arquitectura sigue una separación clara entre presentación, lógica de negocio, acceso a datos e integraciones externas, permitiendo escalar el sistema sin afectar los componentes existentes.

---

# Arquitectura General

```
                        Usuarios
                            │
                            │
                    Navegador Web
                            │
                            ▼
                 Frontend (Next.js)
                            │
                     API REST (HTTPS)
                            │
                            ▼
               Backend (FastAPI / Python)
                            │
        ┌───────────────┬───────────────┬───────────────┐
        │               │               │               │
        ▼               ▼               ▼               ▼
   Gmail API      Supabase DB     Motor IA      Servicios externos
                                       │
                         WhatsApp • Calendario • ERP • CRM
```

---

# Frontend

Tecnología:

- Next.js
- React
- TypeScript

Responsabilidades:

- Autenticación del usuario.
- Dashboard.
- Visualización de correos.
- Gestión de tareas.
- Alertas.
- Administración de cuentas.
- Configuración.

---

# Backend

Tecnología:

- Python
- FastAPI

Responsabilidades:

- API REST.
- Autenticación.
- Gestión de usuarios.
- Gestión de Workspaces.
- Integración con Gmail.
- Comunicación con Supabase.
- Motor de IA.
- Automatizaciones.

---

# Base de Datos

Motor:

- PostgreSQL

Proveedor:

- Supabase

Responsabilidades:

- Usuarios.
- Workspaces.
- Cuentas.
- Correos.
- Tareas.
- Configuración.
- Auditoría.
- Tokens OAuth.

---

# Integraciones Actuales

Implementadas:

- Gmail API
- Google OAuth

Planeadas:

- Microsoft Outlook
- IMAP
- WhatsApp
- Google Calendar
- Microsoft Calendar
- Slack
- Microsoft Teams
- ERP
- CRM

---

# Organización del Proyecto

```
hms-ai-assistant/

├── backend/
│   ├── api/
│   ├── core/
│   ├── database/
│   ├── schemas/
│   ├── services/
│   └── main.py
│
├── frontend/
│
├── supabase/
│   └── migrations/
│
├── docs/
│   └── recovery/
│
└── scripts/
```

---

# Principios Arquitectónicos

El proyecto sigue los siguientes principios:

- Arquitectura modular.
- Separación de responsabilidades.
- Escalabilidad.
- Bajo acoplamiento.
- Alta cohesión.
- Código reutilizable.
- API desacoplada del Frontend.
- Integraciones mediante conectores.

---

# Estado de la Arquitectura

| Componente | Estado |
|------------|--------|
| Frontend | Operativo |
| Backend | Operativo |
| API REST | Operativa |
| Supabase | Operativo |
| Gmail | Funcional |
| OAuth | Parcial |
| Motor IA | En diseño |
| Outlook | Pendiente |
| Automatizaciones | Pendiente |
| Multi Workspace | En desarrollo |

---

# Objetivo Arquitectónico

La arquitectura está siendo preparada para soportar múltiples proveedores de correo, múltiples usuarios, múltiples empresas (Workspaces) y un motor de Inteligencia Artificial centralizado, manteniendo una estructura escalable y fácil de mantener.