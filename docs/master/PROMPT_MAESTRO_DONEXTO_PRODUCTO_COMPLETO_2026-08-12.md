# PROMPT MAESTRO — Donexto (producto completo)

**Fecha:** 2026-08-12  
**Uso:** pegar este documento completo a un agente de desarrollo (Cursor/Codespace) para retomar el producto sin perder contexto.  
**Repo:** `com22fb-bot/hms-ai-assistant` · rama habitual `main`  
**Dueño / titular:** Héctor M. Salcido Roacho · marca **HMSR · MR**  
**Producto público:** **Donexto** — slogan **Do Next To…**

---

## 0. Instrucciones para el agente que lea este prompt

Eres el agente de desarrollo de **Donexto**. Trabajas en español de México con el dueño. Prioriza:

1. **Producto B2C hogar/personal** primero (experiencia Family/Hogar), con motor técnico compartido hacia Profesional después.  
2. **No construir otro Gmail.** Es una **capa de atención** sobre el correo.  
3. **P00 primero** (`docs/ops/P00-pendientes.md`): clasificación (bancos ≠ social), catálogo MX/US, idioma, guía Yahoo.  
4. **Cuenta Donexto ≠ buzón** siempre (P0).  
5. Desarrollo en **Codespace** (el dueño no desarrolla en laptop).  
6. Deploy frontend con **`CLOUDFLARE_API_TOKEN`** (nunca OAuth browser en Codespace: falla por timeout).  
7. No inventar logos “gancho” ni split-screen que desperdicie mitad de pantalla en el login; login = tipografía Donexto + misión/calidad + form (una columna).  
8. No pedir secretos en chat. No force-push a `main`. Commits solo si el dueño lo pide (salvo urgencia explícita de ship).  
9. Validar en prod: https://app.donexto.com solo cambia tras `git pull` **con el commit correcto** + `npm run deploy` autenticado por token.

---

## 1. Qué es el producto final

### 1.1 Definición en una frase

**Donexto** es la capa de atención sobre el correo del hogar: detecta lo que **requiere acción** (dinero, seguridad, paquetes, familia), silencia el ruido promocional y avisa solo cuando importa.

### 1.2 Qué NO es

- No es otro cliente de correo / bandeja alternativa a Gmail.  
- No es un dashboard industrial de fábricas (esa visión B2B “Profesional” es motor futuro, no UI mezclada ahora).  
- No es un chat genérico ni un CRM de ventas.

### 1.3 Promesa y misión (copy canónico)

| Clave | Texto |
|-------|--------|
| Slogan | Do Next To… |
| Promesa | Lo que requiere atención en tu correo. |
| Misión | No somos otra bandeja. Somos la capa de atención: dinero, seguridad, paquetes y familia; silencio para el ruido promocional. |
| Frontera | La cuenta Donexto no es la contraseña de Gmail/Yahoo; el buzón se conecta **después**. |

Fuente código: `frontend/lib/donextoQuality.ts`.

### 1.4 Política de calidad (visible y operativa)

1. **Atención con criterio** — priorizar lo que importa; no ampliar el caos del inbox.  
2. **Cuenta ≠ buzón** — identidad del producto separada del correo vigilado.  
3. **Señales, no ruido** — avisos cuando vale la pena; silencio cuando es promoción.  
4. **Claridad primero · confianza operativa** — no pedir contraseña del buzón en el login Donexto.  
5. Principios históricos (motor): casos/atención > mensajes; notificar eventos de negocio; IA propone, usuario decide; multi-tenant; auditable (`docs/vision/PRODUCT_PRINCIPLES.md`).

### 1.5 Modelo de atención N1 / N2 / N3

| Nivel | Comportamiento |
|-------|----------------|
| **N1** | Atención inmediata / push cuando importa (seguridad, dinero, entregas críticas…). |
| **N2** | Resumen periódico (digest). |
| **N3** | Silencioso (promo / ruido). |

Home post-sync: **AttentionHome** enfocado en N1 (“qué requiere atención”), no conteo de correos.

### 1.6 Experiencia usuario final (producto terminado)

1. Crear **cuenta Donexto** (nombre + email + password).  
2. Verificar email de cuenta.  
3. Conectar **buzón** (Gmail OAuth / Yahoo IMAP / luego Outlook, Apple, dominio privado) y **verificar lectura**.  
4. Ver conteos INBOX/Sent → **sample** (~20) → hasta **10 “requieren atención”**.  
5. Aviso de sync ~**90 días**.  
6. Suscripción **Normal $19.99/mes** (90 días incluidos) o trial 24 h; add-ons historial 180/365.  
7. Sync completo del plan + **Home N1** + push selectivo.  
8. Free restringido **después** (mismo motor, caps duros).  
9. Admin ops para el dueño (`/admin`).

---

## 2. Identidades y políticas de producto (no negociables)

### 2.1 Cuenta Donexto ≠ buzón (P0)

| | Cuenta Donexto | Buzón |
|--|----------------|-------|
| Qué es | Acceso a la app (Supabase Auth) | Correo vigilado |
| Credenciales | Nombre + email + password Donexto | OAuth Gmail o app-password IMAP Yahoo, etc. |
| Momento | Paso 1 | Paso 2 (después del login) |

Doc: `docs/ops/P0-cuenta-donexto-vs-buzon.md`.

### 2.2 Política comercial

| Ítem | Decisión |
|------|----------|
| Plan primario | **Normal $19.99/mes** incluye ~90 días de sync |
| Add-on 180 d | +$9.99 one-time |
| Add-on 365 d | +$16.99 one-time |
| Free | Después de Normal, con restricciones |
| Cobro | Tras buzón verificado **o** trial 24 h |
| Stripe | Principal, **Test Mode** primero |
| PayPal | Secundario |
| Activación lógica | `mailbox_ok` ∧ (`trialing` ∨ `active`) |

### 2.3 Política de notificaciones

- No notificar cada correo.  
- Reglas deterministas antes que IA.  
- Categorías críticas: seguridad, 2FA, cargos, pagos, facturas, servicios, entregas, escuela, salud, viajes, VIP/favoritos.  
- Deduplicación, quiet hours, feedback, auditoría.

### 2.4 Marca

- Nombre: **Donexto**  
- Slogan: **Do Next To…**  
- Colores: teal `#0c8a80` / `#5ecfc4`, magenta `#ff2d6a`, slate `#0a1620`  
- Legal micro (2 líneas): `© HMSR · MR` / `Héctor M. Salcido Roacho`  
- Assets kit: `frontend/public/brand/`  
- **Login de producción (decisión 2026-08-12):** tipografía Donexto + misión/calidad + formulario en **una columna**; **sin** split vacío; **sin** monograma “gancho” inventado como héroe del acceso. Los assets 3D/sobres son para marketing/landing, no para ahogar la marca en el gate.

### 2.5 Privacidad / seguridad

- Login Donexto nunca pide password Gmail/Yahoo.  
- Tokens OAuth/IMAP solo en backend/secrets.  
- Multi-tenant por workspace.  
- Admin por allowlist `ADMIN_EMAILS` (backend).

---

## 3. Plan maestro de desarrollo (P00, luego P0–P12)

**P00 manda ahora** (18 ago 2026): clasificación (Banamex ≠ social), catálogo MX/US, bases de bancos CA/UE/LATAM, idioma ES/EN/FR/IT/PT, guía Yahoo 16 dígitos. Doc: `docs/ops/P00-pendientes.md`.

Orden acordado (continuidad 2026-08-11; **P00 primero**):

| ID | Entrega | Estado |
|----|---------|--------|
| **P00** | Clasificar bien + catálogo + bancos + idioma + guía Yahoo | **Activo — validar en prod** |
| P0 | Cuenta ≠ buzón (UI/copy/signup/gate) | Hecho en código — validar en prod |
| P1 | Matriz buzones (Gmail, Yahoo, Outlook, Apple, dominio privado) | Pendiente |
| P2 | Conectar + **verificar** buzón (`mailbox_verified`) | Después de P00 |
| P3 | Conteos INBOX / Sent | Pendiente |
| P4 | Sample ~20 INBOX + ~20 Sent | Pendiente |
| P5 | Motor hasta 10 “requieren atención” | Pendiente |
| P6 | Modal aviso sync 90 días | Pendiente |
| P7 | Add-ons historial 180/365 | Pendiente |
| P8 | Stripe Normal $19.99 (Test Mode) | Pendiente |
| P9 | Sync full del plan | Pendiente |
| P10 | Home N1 post-sync | Base AttentionHome existe |
| P11 | Free restringido | Después de Normal |
| P12 | Admin con datos reales | Base stub existe |

Respaldo: `docs/recovery/CONTINUIDAD_DONEXTO_2026-08-11.md`.  
Visión dual (Family + Profesional, motor común): `docs/master/2026-08-06-PROMPT-MAESTRO-HMS-V2.md` (histórico; **ruta UI actual = Family/Hogar bajo marca Donexto**).

---

## 4. Cómo lo estamos desarrollando (método y stack)

### 4.1 Stack

| Capa | Tecnología |
|------|------------|
| Frontend app | Next.js (App Router) · OpenNext → Cloudflare Worker `donexto-app` |
| Landing | Cloudflare Pages (`donexto` / donexto.com) |
| Backend | FastAPI (Python) en Railway |
| Auth / DB | Supabase (Auth + Postgres + RLS) |
| Correo | Gmail OAuth · Yahoo IMAP (app password) · ampliar proveedores |
| Pagos (próximo) | Stripe Test Mode → Live; PayPal secundario |
| Repo | GitHub `com22fb-bot/hms-ai-assistant` |

### 4.2 URLs

| Pieza | URL |
|-------|-----|
| App | https://app.donexto.com |
| Worker | https://donexto-app.donexto.workers.dev |
| API | https://hms-ai-assistant-production.up.railway.app |
| Landing | https://donexto.com / Pages |

### 4.3 Flujo de trabajo del dueño

1. Código en Codespace (o push desde máquina del agente a `main`).  
2. `git pull origin main` en Codespace.  
3. Deploy frontend:

```bash
cd /workspaces/hms-ai-assistant/frontend
export CLOUDFLARE_API_TOKEN='TOKEN_REAL'
npx wrangler whoami   # debe listar cuenta sin OAuth browser
npm run deploy
```

**Prohibido en Codespace:** dejar que Wrangler abra OAuth (`localhost:8976`) — hace timeout.  
4. Backend: variables en Railway; migraciones en Supabase SQL.  
5. Validación manual P0 en móvil/desktop.

### 4.4 Estructura relevante del repo

```text
frontend/          # Next.js app.donexto.com
  components/auth/ # LoginScreen, hms-gate.css
  lib/             # donextoQuality.ts, accountVsMailbox.ts, supabase
  app/             # page.tsx, admin/, api/hms proxy
backend/           # FastAPI
supabase/migrations/
landing/donexto/   # marketing site
docs/              # continuidad, ops, master, ADRs
```

### 4.5 Estado técnico conocido (2026-08-12)

- Existe login misión/calidad en `main` (una columna).  
- Producción a veces queda en builds viejos si el deploy falla (OAuth) o si Codespace no tiene el commit.  
- Antes de deploy: `grep dx-auth__quality frontend/components/auth/LoginScreen.tsx` debe encontrar match.  
- Logo oficial PNG puede 404 en prod si no se desplegó el asset; el gate tipográfico no depende de él.

---

## 5. Diccionario de datos (núcleo)

> Resumen operativo. Fuente de verdad: migraciones en `supabase/migrations/`.

### 5.1 Identidad y tenancy

| Entidad | Propósito | Campos clave |
|---------|-----------|--------------|
| `workspaces` | Tenant / hogar / org | `id`, nombre, timestamps |
| `users` / `profiles` | Persona en producto | `id`, email, nombre, metadata |
| `user_workspaces` | Membresía | `user_id`, `workspace_id`, rol |
| Auth (Supabase) | Sesión Donexto | email/password; `user_metadata.full_name` |

### 5.2 Comunicaciones (buzón)

| Entidad | Propósito | Campos clave |
|---------|-----------|--------------|
| `communication_accounts` | Buzón conectado | `workspace_id`, `provider`, `email`, `status`, `last_sync_at` |
| `oauth_credentials` | Tokens Gmail etc. | `account_id`, access/refresh, `expires_at`, scopes |
| `oauth_states` | CSRF OAuth | `state`, `provider`, `expires_at` |
| `communication_threads` | Hilos | `account_id`, subject, participantes, last activity |
| `communication_messages` | Mensajes | thread/account, provider ids, from/to, body refs, fechas, flags |
| `attachments` | Adjuntos | message_id, nombre, mime, size, storage ref |

**Conceptos de producto a persistir (P2+):**  
`mailbox_verified` / `mailbox_ok`, conteos INBOX/Sent, flags de sample, plan de historial (90/180/365).

### 5.3 Inteligencia y trabajo

| Entidad | Propósito |
|---------|-----------|
| `ai_analysis` | Análisis / clasificación / scores |
| Casos inteligentes (sprint 4.3+) | Caso ≠ correo; eventos, notificaciones de caso |
| `tasks` / `reminders` | Seguimiento accionable |
| Categorías / triage (Logística 1) | Clasificación, favoritos, reclassify |
| Learning organizacional | Preferencias aprendidas |

### 5.4 Notificaciones y auditoría

| Entidad | Propósito |
|---------|-----------|
| `notifications` | Canal in-app / push |
| `audit_log` | Trazabilidad |
| Push (web) | Suscripciones browser (módulo push) |

### 5.5 Admin / billing (fundación 2026-08-11)

Migración: `20260811120000_admin_ops_foundation.sql`

| Entidad | Propósito |
|---------|-----------|
| `admin_feedback` | Quejas / sugerencias / bugs |
| `billing_customers` | Cliente de cobro (stripe/paypal/manual) |
| `billing_subscriptions` | Estado suscripción |
| (stubs) | promociones, métricas host, audit ops |

### 5.6 Diccionario semántico (producto)

| Término | Significado |
|---------|-------------|
| Cuenta Donexto | Identidad de producto |
| Buzón | Mailbox conectado |
| Atención / N1 | Ítems que requieren acción ahora |
| Sample | Muestra inicial (~20) antes del sync full |
| Sync 90d | Ventana incluida en Normal |
| Caso | Unidad de trabajo (no un solo mensaje) |
| Evidencia | Mensajes que sustentan un caso |
| Provider | gmail, yahoo, outlook, apple, imap… |

---

## 6. Características funcionales (mapa)

### 6.1 Ya en camino / base existente

- Auth Donexto (signup con nombre, signin, magic link, reset).  
- Copy P0 cuenta ≠ buzón.  
- Conexión Gmail OAuth y Yahoo IMAP (ops docs).  
- Proxy API HMS desde frontend.  
- AttentionHome (base N1).  
- Clasificación / logística / favoritos / búsqueda (módulos previos).  
- Push notifications (módulo).  
- Admin stub `/admin` + API `/admin/*`.  
- Landing marketing Donexto.  
- Login misión/calidad tipográfico (código en main).

### 6.2 A construir (producto final Family)

- Matriz completa de proveedores + verify.  
- Onboarding sample → top 10 atención.  
- Billing Stripe + add-ons historial.  
- Sync durable por plan.  
- Push N1 afinado + digest N2.  
- Explicación de por qué un ítem requiere atención.  
- Privacidad familiar multi-miembro (fase posterior).  
- Free caps.  
- Admin con métricas reales (Stripe + Railway).

### 6.3 Futuro (no mezclar UI ahora)

- **HMS Profesional:** casos operativos B2B, responsables, métricas org.  
- Motor compartido; experiencias separadas.

---

## 7. Criterios de aceptación del producto final (Definition of Done)

Un usuario nuevo en EE. UU./México puede:

1. Crear cuenta Donexto y entender que **no** es Gmail.  
2. Conectar Gmail o Yahoo y ver confirmación de lectura.  
3. Ver en minutos una lista corta de lo que **requiere atención** (no 5 000 mails).  
4. Recibir push solo en N1 relevante.  
5. Pagar Normal en test/live y ampliar historial si quiere.  
6. Abrir el mensaje/caso original cuando lo necesite.  
7. El dueño opera `/admin` con feedback y billing básico.

UI de acceso: confiable, una columna, misión/calidad legibles, marca **Donexto** tipográfica dominante.

---

## 8. Anti-patrones (no hacer)

- Pedir password del buzón en el login Donexto.  
- Mostrar inbox completo como home.  
- Notificar cada correo.  
- Mezclar UI Profesional industrial con Family.  
- Inventar logos/monogramas no aprobados como héroe del login.  
- Split-screen que deje media pantalla vacía “de adorno”.  
- Deploy con OAuth Wrangler en Codespace.  
- Deploy sin confirmar que `main` trae el commit esperado.  
- Commitear `.env` o secretos.

---

## 9. Checklist inmediato para el próximo agente

1. Leer y ejecutar **P00**: `docs/ops/P00-pendientes.md` (merge PR #5, Railway v4, reclasificar, Banamex en Avisos, idioma, guía Yahoo).  
2. Confirmar en Codespace: `git log -1 --oneline`.  
3. Deploy frontend con `CLOUDFLARE_API_TOKEN` + `wrangler whoami` OK + `cd frontend && npm run deploy`.  
4. No abrir P2 / Stripe hasta que Héctor cierre P00.  
5. No reabrir rediseños de login sin brief escrito del dueño.

---

## 10. Frase de arranque (copiar/pegar)

> Continúa **Donexto** (`com22fb-bot/hms-ai-assistant`, `main`): **P00 primero** (`docs/ops/P00-pendientes.md`) — Banamex no es social, catálogo MX/US, bancos CA/UE/LATAM, idioma ES/EN/FR/IT/PT, guía Yahoo 16 dígitos. Luego cuenta ≠ buzón y P2. Stack Next/OpenNext Cloudflare + FastAPI Railway + Supabase. No otro Gmail. Deploy solo con API token.
