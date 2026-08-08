# HMS AI Assistant - Database Schema v1

> Estado: Draft v1.0
> Sprint: 0
> Base de datos: PostgreSQL (Supabase)

---

# Objetivo

Definir el modelo de datos definitivo de HMS AI Assistant antes de generar las migraciones SQL.

Este documento describe:

- Dominios del sistema.
- Entidades.
- Responsabilidades.
- Relaciones.
- Restricciones.
- Estrategia de crecimiento.

---

# Dominios del sistema

La base de datos se divide en dominios funcionales.

## 1. Identity

Responsable de la identidad del usuario.

Entidades:

- profiles
- registered_devices

---

## 2. Workspace

Responsable del aislamiento multiempresa.

Entidades:

- workspaces
- workspace_members
- workspace_roles

---

## 3. Mail

Responsable del acceso al correo.

Entidades:

- mailboxes
- mail_accounts
- mail_account_access
- sync_checkpoints

---

## 4. Messaging

Responsable del contenido sincronizado.

Entidades:

- emails
- email_attachments
- email_labels

---

## 5. AI

Responsable del procesamiento inteligente.

Entidades:

- ai_analysis
- ai_entities

---

## 6. Productivity

Responsable de tareas y recordatorios.

Entidades:

- tasks
- alerts

---

## 7. Security

Responsable de auditoría y seguridad.

Entidades:

- audit_events
- login_history
- retention_policies
- legal_holds

---

# Principios

## Multi Tenant

Toda la información deberá pertenecer a un Workspace.

---

## Provider Agnostic

El dominio del negocio nunca dependerá de Gmail.

---

## Least Privilege

Los permisos se otorgarán explícitamente.

---

## Audit First

Las acciones importantes deberán registrarse.

---

## Soft Delete

Las entidades empresariales no deberán eliminarse físicamente de inmediato.

---

## UUID

Todas las claves primarias utilizarán UUID.

---

## UTC

Todas las fechas se almacenarán en UTC.

---

## JSONB

Solo se utilizará para datos dinámicos que no justifiquen columnas propias.
---

# Modelo estructural detallado

## Convenciones generales

Las tablas nuevas seguirán estas reglas:

- Claves primarias: `uuid`.
- Fechas: `timestamptz`.
- Identificadores: nombres en `snake_case`.
- Eliminación lógica mediante `deleted_at`, cuando corresponda.
- Registros creados por usuarios mediante `created_by`, cuando sea necesario.
- Toda entidad empresarial deberá estar asociada directa o indirectamente a un `workspace`.
- Los secretos y tokens nunca deberán devolverse al frontend.
- Las claves foráneas deberán definir expresamente su comportamiento `ON DELETE`.
- Los estados y tipos deberán validarse mediante `CHECK`, enums de PostgreSQL o tablas de catálogo.
- Los campos `created_at` utilizarán UTC y valor predeterminado `now()`.

---

# 1. Identity Domain

## 1.1 profiles

### Responsabilidad

Extender la identidad administrada por Supabase Auth.

Supabase Auth conservará:

- autenticación;
- contraseña;
- proveedores de acceso;
- sesiones;
- recuperación de cuenta.

La tabla `profiles` conservará información funcional de la persona.

### Columnas

| Columna | Tipo | Nulo | Descripción |
|---|---|---:|---|
| `id` | `uuid` | No | Mismo identificador de `auth.users.id`. |
| `full_name` | `text` | Sí | Nombre visible de la persona. |
| `phone` | `text` | Sí | Teléfono normalizado. |
| `language` | `text` | No | Idioma preferido. Predeterminado: `es-MX`. |
| `timezone` | `text` | No | Zona horaria IANA. Predeterminado: `America/Chihuahua`. |
| `status` | `text` | No | Estado funcional del perfil. |
| `last_active_at` | `timestamptz` | Sí | Última actividad conocida. |
| `created_at` | `timestamptz` | No | Fecha de creación. |
| `updated_at` | `timestamptz` | No | Última modificación. |
| `deleted_at` | `timestamptz` | Sí | Eliminación lógica. |

### Restricciones

- `id` será PK y FK a `auth.users(id)`.
- `status` admitirá inicialmente:
  - `active`
  - `suspended`
  - `disabled`
- El idioma deberá usar un código compatible con BCP 47.
- La zona horaria deberá utilizar un identificador IANA.

### Índices

- Índice por `status`.
- Índice parcial por `deleted_at IS NULL`.

### RLS preliminar

- Una persona puede consultar su propio perfil.
- Una persona puede modificar campos permitidos de su propio perfil.
- Los administradores autorizados podrán visualizar información limitada de miembros de su workspace.
- Ningún usuario podrá modificar directamente el `status` de otro usuario desde el cliente.

---

## 1.2 registered_devices

### Responsabilidad

Registrar dispositivos y credenciales criptográficas asociadas a una persona.

No se utilizarán direcciones MAC como identidad.

### Columnas

| Columna | Tipo | Nulo | Descripción |
|---|---|---:|---|
| `id` | `uuid` | No | Identificador del dispositivo registrado. |
| `profile_id` | `uuid` | No | Persona propietaria del registro. |
| `device_name` | `text` | Sí | Nombre asignado por el usuario. |
| `platform` | `text` | No | Plataforma del dispositivo. |
| `app_version` | `text` | Sí | Versión de la aplicación. |
| `public_key` | `text` | Sí | Clave pública o referencia criptográfica. |
| `push_token_encrypted` | `text` | Sí | Token cifrado para notificaciones. |
| `trust_status` | `text` | No | Nivel de confianza del dispositivo. |
| `risk_level` | `text` | No | Nivel de riesgo calculado. |
| `first_seen_at` | `timestamptz` | No | Primer registro. |
| `last_seen_at` | `timestamptz` | No | Última actividad. |
| `trusted_at` | `timestamptz` | Sí | Momento en que fue aprobado. |
| `revoked_at` | `timestamptz` | Sí | Momento de revocación. |
| `created_at` | `timestamptz` | No | Fecha de creación. |

### Valores iniciales

`platform`:

- `web`
- `android`
- `ios`
- `huawei`
- `windows`
- `macos`
- `linux`

`trust_status`:

- `pending`
- `trusted`
- `restricted`
- `revoked`

`risk_level`:

- `low`
- `medium`
- `high`
- `critical`

### Relaciones

- `registered_devices.profile_id → profiles.id`
- Relación `profiles 1:N registered_devices`.

### Política de eliminación

Al eliminar una cuenta:

- los dispositivos deberán revocarse;
- la auditoría histórica deberá conservar la referencia necesaria;
- no deberá eliminarse silenciosamente evidencia de seguridad.

---

# 2. Workspace Domain

## 2.1 workspaces

### Responsabilidad

Representar la frontera principal de aislamiento de información y permisos.

### Columnas

| Columna | Tipo | Nulo | Descripción |
|---|---|---:|---|
| `id` | `uuid` | No | Identificador del workspace. |
| `workspace_type` | `text` | No | Tipo personal u organización. |
| `name` | `text` | No | Nombre visible. |
| `slug` | `text` | No | Identificador legible único. |
| `status` | `text` | No | Estado operativo. |
| `created_by` | `uuid` | No | Persona que creó el workspace. |
| `personal_owner_id` | `uuid` | Sí | Propietario cuando sea personal. |
| `settings` | `jsonb` | No | Configuración no estructural. |
| `created_at` | `timestamptz` | No | Fecha de creación. |
| `updated_at` | `timestamptz` | No | Última modificación. |
| `deleted_at` | `timestamptz` | Sí | Eliminación lógica. |

### Valores iniciales

`workspace_type`:

- `personal`
- `organization`

`status`:

- `active`
- `suspended`
- `archived`
- `pending_deletion`

### Restricciones

- `slug` deberá ser único.
- Un workspace personal deberá tener `personal_owner_id`.
- Un workspace organizacional deberá tener `personal_owner_id IS NULL`.
- Cada perfil tendrá como máximo un workspace personal activo.
- `settings` tendrá como valor predeterminado `{}`.
- El workspace personal se creará automáticamente después del registro.

### Índices

- Índice único por `slug`.
- Índice por `created_by`.
- Índice por `personal_owner_id`.
- Índice parcial para workspaces activos.
- Índice único parcial para garantizar un workspace personal activo por perfil.

### Eliminación

Los workspaces no se eliminarán físicamente de forma inmediata.

La eliminación deberá considerar:

- retención;
- legal hold;
- auditoría;
- buzones conectados;
- archivos;
- tareas;
- obligaciones contractuales.

---

## 2.2 workspace_members

### Responsabilidad

Relacionar personas con workspaces y asignarles una condición de membresía.

### Columnas

| Columna | Tipo | Nulo | Descripción |
|---|---|---:|---|
| `id` | `uuid` | No | Identificador de membresía. |
| `workspace_id` | `uuid` | No | Workspace relacionado. |
| `profile_id` | `uuid` | No | Persona relacionada. |
| `role` | `text` | No | Rol general dentro del workspace. |
| `status` | `text` | No | Estado de membresía. |
| `invited_by` | `uuid` | Sí | Miembro que realizó la invitación. |
| `invited_at` | `timestamptz` | Sí | Fecha de invitación. |
| `joined_at` | `timestamptz` | Sí | Fecha de aceptación. |
| `suspended_at` | `timestamptz` | Sí | Fecha de suspensión. |
| `revoked_at` | `timestamptz` | Sí | Fecha de revocación. |
| `created_at` | `timestamptz` | No | Fecha de creación. |
| `updated_at` | `timestamptz` | No | Última modificación. |

### Roles iniciales

- `owner`
- `admin`
- `manager`
- `operator`
- `viewer`
- `auditor`

### Estados iniciales

- `invited`
- `active`
- `suspended`
- `revoked`

### Restricciones

- La combinación `workspace_id + profile_id` deberá ser única.
- Todo workspace activo deberá conservar al menos un miembro `owner`.
- Un usuario revocado no deberá acceder al workspace.
- El propietario de un workspace personal será su único `owner`.
- No se permitirá revocar al último propietario activo sin transferir antes la propiedad.

### Relaciones

- `workspace_members.workspace_id → workspaces.id`
- `workspace_members.profile_id → profiles.id`
- `workspace_members.invited_by → workspace_members.id`

### Índices

- Índice único por `workspace_id, profile_id`.
- Índice por `profile_id, status`.
- Índice por `workspace_id, role`.
- Índice parcial para membresías activas.

### Nota de diseño

Los roles generales del workspace no sustituyen los permisos específicos de buzón.

Un miembro puede ser:

- `admin` del workspace;
- `viewer` de un buzón;
- `operator` de otro buzón.

---

# 3. Mail Domain

## 3.1 mailboxes

### Responsabilidad

Representar el buzón lógico del negocio.

Ejemplos:

- Ventas
- Compras
- Dirección General
- Recursos Humanos
- Correo personal de Héctor

El buzón lógico permanece aunque cambie el proveedor técnico.

### Columnas

| Columna | Tipo | Nulo | Descripción |
|---|---|---:|---|
| `id` | `uuid` | No | Identificador del buzón lógico. |
| `workspace_id` | `uuid` | No | Workspace propietario. |
| `name` | `text` | No | Nombre funcional del buzón. |
| `description` | `text` | Sí | Descripción operativa. |
| `mailbox_type` | `text` | No | Tipo personal, compartido o departamental. |
| `status` | `text` | No | Estado funcional. |
| `default_sender_name` | `text` | Sí | Nombre predeterminado al enviar. |
| `created_by` | `uuid` | No | Miembro que creó el buzón. |
| `created_at` | `timestamptz` | No | Fecha de creación. |
| `updated_at` | `timestamptz` | No | Última modificación. |
| `deleted_at` | `timestamptz` | Sí | Eliminación lógica. |

### Tipos iniciales

- `personal`
- `shared`
- `department`
- `service`

### Estados iniciales

- `active`
- `inactive`
- `archived`
- `pending_deletion`

### Restricciones

- El nombre deberá ser único dentro del workspace entre buzones activos.
- Los buzones personales solo podrán existir dentro de un workspace personal o con autorización explícita.
- Un buzón podrá conservar historial aunque se desconecte el proveedor.

### Relaciones

- `mailboxes.workspace_id → workspaces.id`
- `mailboxes.created_by → workspace_members.id`

### Índices

- Índice por `workspace_id`.
- Índice único parcial por `workspace_id, lower(name)` donde `deleted_at IS NULL`.
- Índice por `workspace_id, status`.

---

## 3.2 mail_accounts

### Responsabilidad

Representar una dirección de correo y su identidad dentro de un proveedor.

Ejemplos:

- `ventas@empresa.com` en Google Workspace.
- `creechihuahua@yahoo.com.mx` en Yahoo.
- `compras@empresa.com` en Microsoft 365.

No almacenará directamente tokens OAuth.

### Columnas

| Columna | Tipo | Nulo | Descripción |
|---|---|---:|---|
| `id` | `uuid` | No | Identificador de la cuenta. |
| `mailbox_id` | `uuid` | No | Buzón lógico relacionado. |
| `provider` | `text` | No | Proveedor de correo. |
| `provider_account_id` | `text` | Sí | Identificador interno del proveedor. |
| `email_address` | `citext` | No | Dirección de correo normalizada. |
| `display_name` | `text` | Sí | Nombre reportado por el proveedor. |
| `account_type` | `text` | No | Tipo personal, empresarial o compartido. |
| `status` | `text` | No | Estado operativo de la cuenta. |
| `is_primary` | `boolean` | No | Indica la conexión principal del buzón. |
| `last_successful_sync_at` | `timestamptz` | Sí | Última sincronización correcta. |
| `created_at` | `timestamptz` | No | Fecha de creación. |
| `updated_at` | `timestamptz` | No | Última modificación. |
| `disconnected_at` | `timestamptz` | Sí | Fecha de desconexión. |
| `deleted_at` | `timestamptz` | Sí | Eliminación lógica. |

### Proveedores iniciales

- `gmail`
- `google_workspace`
- `yahoo`
- `outlook`
- `microsoft_365`
- `exchange`
- `imap`

### Estados iniciales

- `pending`
- `connected`
- `degraded`
- `reauthorization_required`
- `disconnected`
- `disabled`

### Restricciones

- `email_address` deberá ser insensible a mayúsculas mediante `citext`.
- La combinación `provider + provider_account_id` será única cuando exista el identificador.
- Solo una cuenta activa podrá ser `is_primary = true` por buzón.
- Una dirección podrá conservarse desconectada para preservar historial y auditoría.

### Relaciones

- `mail_accounts.mailbox_id → mailboxes.id`

### Índices

- Índice por `mailbox_id`.
- Índice por `email_address`.
- Índice por `provider, status`.
- Índice único parcial para una cuenta principal activa por buzón.

---

## 3.3 provider_connections

### Responsabilidad

Almacenar la conexión técnica y el estado de autorización con el proveedor.

Esta tabla estará separada de `mail_accounts` para aislar secretos y detalles de infraestructura.

### Columnas

| Columna | Tipo | Nulo | Descripción |
|---|---|---:|---|
| `id` | `uuid` | No | Identificador de conexión. |
| `mail_account_id` | `uuid` | No | Cuenta asociada. |
| `auth_type` | `text` | No | Método de autenticación. |
| `access_token_encrypted` | `text` | Sí | Token cifrado. |
| `refresh_token_encrypted` | `text` | Sí | Refresh token cifrado. |
| `token_expires_at` | `timestamptz` | Sí | Expiración del token. |
| `scopes` | `text[]` | No | Permisos autorizados. |
| `connection_status` | `text` | No | Estado técnico. |
| `failure_count` | `integer` | No | Fallos consecutivos. |
| `last_error_code` | `text` | Sí | Código del último error. |
| `last_error_message` | `text` | Sí | Mensaje sanitizado. |
| `last_error_at` | `timestamptz` | Sí | Momento del último error. |
| `last_validated_at` | `timestamptz` | Sí | Última validación. |
| `created_at` | `timestamptz` | No | Fecha de creación. |
| `updated_at` | `timestamptz` | No | Última modificación. |
| `revoked_at` | `timestamptz` | Sí | Fecha de revocación. |

### Métodos de autenticación

- `oauth2`
- `app_password`
- `service_account`
- `imap_credentials`

### Estados

- `pending`
- `active`
- `expired`
- `invalid`
- `revoked`
- `error`

### Reglas de seguridad

- El frontend no tendrá acceso directo a esta tabla.
- Los tokens deberán cifrarse antes de almacenarse.
- Los mensajes de error deberán sanitizarse.
- Nunca deberán almacenarse contraseñas ordinarias de Gmail, Yahoo o Microsoft.
- El backend utilizará acceso privilegiado controlado.
- La rotación y revocación deberán generar eventos de auditoría.

### Relaciones

- `provider_connections.mail_account_id → mail_accounts.id`
- Inicialmente se permitirá una conexión activa por cuenta.
- El modelo podrá conservar conexiones anteriores revocadas para auditoría.

---

## 3.4 mailbox_access

### Responsabilidad

Definir el acceso específico de miembros a cada buzón lógico.

### Columnas

| Columna | Tipo | Nulo | Descripción |
|---|---|---:|---|
| `id` | `uuid` | No | Identificador del permiso. |
| `mailbox_id` | `uuid` | No | Buzón autorizado. |
| `workspace_member_id` | `uuid` | No | Miembro autorizado. |
| `access_role` | `text` | No | Rol específico sobre el buzón. |
| `can_read` | `boolean` | No | Puede consultar mensajes. |
| `can_send` | `boolean` | No | Puede enviar o responder. |
| `can_assign` | `boolean` | No | Puede asignar tareas o responsables. |
| `can_archive` | `boolean` | No | Puede archivar mensajes. |
| `can_delete` | `boolean` | No | Puede solicitar eliminación. |
| `can_export` | `boolean` | No | Puede exportar información. |
| `can_manage_access` | `boolean` | No | Puede administrar permisos del buzón. |
| `granted_by` | `uuid` | No | Miembro que otorgó el acceso. |
| `granted_at` | `timestamptz` | No | Fecha de autorización. |
| `expires_at` | `timestamptz` | Sí | Caducidad opcional. |
| `revoked_at` | `timestamptz` | Sí | Fecha de revocación. |
| `created_at` | `timestamptz` | No | Fecha de creación. |
| `updated_at` | `timestamptz` | No | Última modificación. |

### Roles de buzón

- `mailbox_owner`
- `mailbox_admin`
- `operator`
- `viewer`
- `auditor`

### Restricciones

- La combinación `mailbox_id + workspace_member_id` deberá ser única entre accesos vigentes.
- El miembro y el buzón deberán pertenecer al mismo workspace.
- La autorización se denegará por defecto.
- Los permisos booleanos permitirán ajustes más precisos que el rol general.
- `can_delete` autorizará solicitar eliminación, no necesariamente destruir físicamente.
- `can_manage_access` será una operación privilegiada.

### Índices

- Índice por `mailbox_id`.
- Índice por `workspace_member_id`.
- Índice único parcial para accesos no revocados.
- Índice por `expires_at` para revocación automática.

---

## 3.5 sync_checkpoints

### Responsabilidad

Registrar el progreso de sincronización sin mezclarlo con las entidades de negocio.

### Columnas

| Columna | Tipo | Nulo | Descripción |
|---|---|---:|---|
| `id` | `uuid` | No | Identificador del checkpoint. |
| `mail_account_id` | `uuid` | No | Cuenta sincronizada. |
| `sync_type` | `text` | No | Tipo de sincronización. |
| `provider_cursor` | `text` | Sí | Cursor del proveedor. |
| `history_id` | `text` | Sí | Identificador incremental cuando aplique. |
| `date_from` | `timestamptz` | Sí | Inicio del intervalo. |
| `date_to` | `timestamptz` | Sí | Fin del intervalo. |
| `status` | `text` | No | Estado del proceso. |
| `processed_items` | `bigint` | No | Elementos procesados. |
| `failed_items` | `bigint` | No | Elementos con error. |
| `last_error` | `text` | Sí | Error sanitizado. |
| `started_at` | `timestamptz` | Sí | Inicio del trabajo. |
| `completed_at` | `timestamptz` | Sí | Finalización. |
| `updated_at` | `timestamptz` | No | Última modificación. |
| `created_at` | `timestamptz` | No | Fecha de creación. |

### Tipos de sincronización

- `initial_recent`
- `initial_year`
- `historical`
- `incremental`
- `folder`
- `reconciliation`

### Estados

- `pending`
- `running`
- `paused`
- `completed`
- `failed`
- `cancelled`

### Reglas

- Los procesos deberán ser idempotentes.
- Los checkpoints deberán permitir reanudar después de una interrupción.
- Los cursores no deberán interpretarse fuera del adaptador del proveedor.
- Cada intento deberá conservar suficiente información para diagnóstico.
# 4. Messaging Domain

## Objetivo

Administrar el contenido sincronizado de los proveedores de correo.

El dominio Messaging es independiente del proveedor.

No importa si el mensaje proviene de:

- Gmail
- Yahoo
- Outlook
- Microsoft 365
- IMAP

Todos los mensajes deberán almacenarse con la misma estructura.

---

## 4.1 emails

### Responsabilidad

Representar un correo electrónico sincronizado.

### Relaciones

mail_account

↓

emails

↓

attachments

↓

ai_analysis

↓

tasks

---

### Columnas principales

| Campo | Tipo |
|--------|------|
| id | uuid |
| mail_account_id | uuid |
| provider_message_id | text |
| provider_thread_id | text |
| internet_message_id | text |
| folder | text |
| subject | text |
| sender_name | text |
| sender_email | citext |
| recipients | jsonb |
| cc | jsonb |
| bcc | jsonb |
| body_text | text |
| body_html | text |
| snippet | text |
| received_at | timestamptz |
| sent_at | timestamptz |
| is_read | boolean |
| is_starred | boolean |
| is_archived | boolean |
| is_deleted | boolean |
| importance | text |
| sensitivity | text |
| created_at | timestamptz |
| updated_at | timestamptz |

---

### Índices

provider_message_id

provider_thread_id

received_at DESC

mail_account_id + received_at DESC

sender_email

subject

---

### Restricciones

provider_message_id deberá ser único por cuenta.

Los mensajes nunca deberán duplicarse.

El historial deberá conservarse incluso después de desconectar una cuenta.

---

## 4.2 email_attachments

Representa archivos adjuntos.

Columnas:

- id
- email_id
- filename
- mime_type
- size_bytes
- provider_attachment_id
- storage_path
- sha256
- created_at

---

## 4.3 email_labels

Representa etiquetas internas y del proveedor.

Ejemplos:

INBOX

IMPORTANT

STARRED

CUSTOM

AI
# 5. AI Domain

## Objetivo

Transformar mensajes en información estructurada.

La IA nunca modificará el correo original.

Su función será generar conocimiento adicional.

---

## 5.1 ai_analysis

Representa una ejecución del motor de IA.

### Columnas

- id
- email_id
- model
- model_version
- prompt_version
- language
- confidence
- execution_time_ms
- token_input
- token_output
- estimated_cost
- status
- analyzed_at
- created_at

Estados:

- pending
- running
- completed
- failed

---

## 5.2 ai_findings

Representa información detectada por IA.

Cada registro corresponde a un hallazgo.

Ejemplos:

- payment
- deadline
- commitment
- person
- company
- amount
- project
- risk
- location
- phone
- invoice
- contract

### Columnas

- id
- analysis_id
- finding_type
- label
- normalized_value
- confidence
- source_text
- created_at

---

## Relaciones

Email

1 ---- N AI Analysis

AI Analysis

1 ---- N AI Findings
# 6. Productivity Domain

## Objetivo

Administrar las tareas, compromisos, recordatorios y alertas generadas por el sistema.

Las tareas pueden originarse de múltiples fuentes y no dependen exclusivamente de un correo electrónico.

---

## 6.1 tasks

### Responsabilidad

Representa una acción que debe realizar un usuario o un equipo.

Una tarea puede ser creada:

- Manualmente
- Por IA
- Desde un correo
- Desde un documento
- Desde futuras integraciones

---

### Columnas

| Campo | Tipo |
|--------|------|
| id | uuid |
| workspace_id | uuid |
| mailbox_id | uuid |
| email_id | uuid nullable |
| ai_finding_id | uuid nullable |
| created_by | uuid |
| assigned_to | uuid nullable |
| title | text |
| description | text |
| task_source | text |
| priority | text |
| status | text |
| due_date | timestamptz |
| completed_at | timestamptz |
| metadata | jsonb |
| created_at | timestamptz |
| updated_at | timestamptz |
| deleted_at | timestamptz |

---

### Valores iniciales

#### task_source

- manual
- email
- ai
- document
- api

#### priority

- low
- normal
- high
- critical

#### status

- pending
- in_progress
- waiting
- completed
- cancelled

---

### Restricciones

Una tarea siempre pertenece a un Workspace.

Una tarea puede existir sin correo asociado.

Si existe un correo relacionado, deberá mantenerse el vínculo incluso cuando el mensaje sea archivado.

---

### Índices

workspace_id

assigned_to

status

priority

due_date

created_at DESC

---

## 6.2 task_comments

### Responsabilidad

Registrar el historial de conversaciones sobre una tarea.

### Columnas

- id
- task_id
- author_id
- comment
- created_at

---

## 6.3 reminders

### Responsabilidad

Programar recordatorios para tareas.

### Columnas

- id
- task_id
- remind_at
- notification_channel
- status
- sent_at
- created_at

---

### Canales iniciales

- email
- push
- whatsapp
- sms

---

## Relaciones

Workspace

1 ---- N Tasks

Task

1 ---- N Comments

Task

1 ---- N Reminders
# 7. Security Domain

## Objetivo

Garantizar la trazabilidad, seguridad, cumplimiento normativo y administración de integraciones de HMS AI Assistant.

Toda acción importante deberá poder ser auditada.

---

## 7.1 audit_events

### Responsabilidad

Registrar cualquier acción relevante realizada por usuarios o por el sistema.

Nunca deberá eliminarse un evento de auditoría.

---

### Columnas

| Campo | Tipo |
|--------|------|
| id | uuid |
| workspace_id | uuid |
| actor_id | uuid nullable |
| entity_type | text |
| entity_id | uuid nullable |
| action | text |
| source | text |
| ip_address | inet |
| user_agent | text |
| metadata | jsonb |
| created_at | timestamptz |

---

### Acciones iniciales

- login
- logout
- create
- update
- delete
- restore
- synchronize
- analyze
- export
- import
- permission_change

---

### Restricciones

Los registros de auditoría son inmutables.

No deberán modificarse.

---

## 7.2 retention_policies

### Responsabilidad

Definir cuánto tiempo conservar la información.

### Columnas

- id
- workspace_id
- entity_type
- retention_days
- archive_after_days
- delete_after_days
- created_at
- updated_at

---

## 7.3 legal_holds

### Responsabilidad

Impedir la eliminación de información por motivos legales o administrativos.

### Columnas

- id
- workspace_id
- entity_type
- entity_id
- reason
- created_by
- created_at
- expires_at

---

## 7.4 api_keys

### Responsabilidad

Administrar claves utilizadas por integraciones externas.

### Columnas

- id
- workspace_id
- name
- key_hash
- permissions
- last_used_at
- expires_at
- status
- created_at

---

## 7.5 webhooks

### Responsabilidad

Permitir que sistemas externos reciban eventos generados por HMS AI Assistant.

### Columnas

- id
- workspace_id
- name
- endpoint_url
- secret
- subscribed_events
- status
- last_delivery_at
- created_at

---

## Relaciones

Workspace

1 ---- N Audit Events

Workspace

1 ---- N Retention Policies

Workspace

1 ---- N API Keys

Workspace

1 ---- N Webhooks
# 8. Knowledge Domain

## Objetivo

Representar entidades de negocio detectadas por IA y sus relaciones.

Este dominio permitirá construir una base de conocimiento independiente del proveedor de correo.

---

## 8.1 knowledge_entities

### Responsabilidad

Representar una entidad identificada por la IA.

### Columnas

- id
- workspace_id
- entity_type
- canonical_name
- normalized_value
- confidence
- metadata
- created_at
- updated_at

---

### entity_type

- person
- company
- project
- contract
- invoice
- payment
- document
- location
- phone
- email
- organization
- vehicle
- asset

---

## 8.2 knowledge_relationships

### Responsabilidad

Relacionar entidades.

Ejemplos:

Empresa

↓

Tiene

↓

Proyecto

Persona

↓

Pertenece a

↓

Empresa

Factura

↓

Corresponde a

↓

Contrato

---

### Columnas

- id
- workspace_id
- source_entity_id
- target_entity_id
- relationship_type
- confidence
- created_at
# 9. Event Domain

## Objetivo

Coordinar la comunicación entre los diferentes módulos del sistema mediante eventos internos.

Los eventos representan hechos ocurridos y nunca deberán modificarse.

---

## 9.1 system_events

### Responsabilidad

Registrar eventos importantes generados por la plataforma.

### Columnas

- id
- workspace_id
- event_type
- entity_type
- entity_id
- payload
- processed
- processed_at
- created_at

---

### Eventos iniciales

MailConnected

MailDisconnected

EmailReceived

EmailUpdated

EmailDeleted

AIAnalysisStarted

AIAnalysisCompleted

TaskCreated

TaskAssigned

TaskCompleted

ReminderTriggered

NotificationSent

UserInvited

WorkspaceCreated

SyncStarted

SyncCompleted

SyncFailed