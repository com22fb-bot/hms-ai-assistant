# OAuth de identidad en Supabase Auth (Crear cuenta)

Alta de cuenta Donexto: **Crear cuenta** → proveedor → portal OAuth de ese correo.
No sustituye el Paso 2 (buzón Gmail API / IMAP Yahoo). Ver [GOOGLE_OAUTH_DONEXTO.md](./GOOGLE_OAUTH_DONEXTO.md).

No hay secretos en este documento.

Rutas del dashboard verificadas en docs oficiales y código de Studio (agosto 2026).
El ítem ya **no** se llama solo “Providers”: es **Sign In / Providers**.

## Callback y Site URL (todos los proveedores)

En cada consola OAuth (Google Cloud, Azure, Apple) registra:

```text
https://tgirnpystoydvbxlvlzz.supabase.co/auth/v1/callback
```

Ese host es el `NEXT_PUBLIC_SUPABASE_URL` de producción (`app.donexto.com`).
Si abres **otro** proyecto en el dashboard, el callback no coincidirá.

En Supabase → **Authentication** → **URL Configuration**
(enlace: https://supabase.com/dashboard/project/tgirnpystoydvbxlvlzz/auth/url-configuration):

- **Site URL:** `https://app.donexto.com`
- **Redirect URLs:** `https://app.donexto.com/`, `https://app.donexto.com/**` y, en local, `http://localhost:3000/` (o `http://localhost:3000/**`)

## Qué activar (en este orden)

Ruta canónica 2026:

**Authentication** (barra izquierda del proyecto) → grupo **Configuration** → **Sign In / Providers** → pestaña **Supabase Auth**.

Enlace directo Google:
https://supabase.com/dashboard/project/tgirnpystoydvbxlvlzz/auth/providers?provider=Google

Si no ves “Providers”, abre esa URL, o busca **Sign In / Providers**. Las rutas viejas
`/auth/settings` y `/settings/auth` redirigen a `/auth/providers`.

### 1. Google — prueba primero

**Sign In / Providers** → **Google** → interruptor **Enable Sign in with Google**.
Campos: **Client IDs** y **Client Secret (for OAuth)** del cliente OAuth tipo **Web**
en Google Cloud (Google Auth Platform → Clients, o APIs & Services → Credentials).
En ese cliente, el callback de arriba. **No quites** el callback de Railway del buzón
(`https://hms-ai-assistant-production.up.railway.app/auth/google/callback`).

Crear cuenta → **Gmail** debe abrir el consentimiento de Google.
Si falla: la UI dice `Falta activar Google en Supabase Auth`.

### 2. Azure (Hotmail / Outlook / Microsoft)

**Sign In / Providers** → **Azure** → **Azure enabled**.
App registration en Microsoft Entra (Azure AD). Redirect URI = el callback de Supabase.

Crear cuenta → **Hotmail** abre el portal de Microsoft (`provider: 'azure'`).

### 3. Apple

**Sign In / Providers** → **Apple** → **Enable Sign in with Apple**.
Services ID + Key en Apple Developer. Return URL = el callback de Supabase.

Crear cuenta → **Apple** abre el portal de Apple.

### Yahoo

`supabase-js` **no** incluye `yahoo` como Provider de Auth.
El acceso empieza por el correo. Si ya hay cuenta, Donexto abre el sitio
de Yahoo (`POST /auth/yahoo/login`, `login_hint`) para firmar. Si no hay
cuenta, pide confirmar el correo y el alta usa `intent=signup`. IMAP lee
el buzón con el token OAuth (`OAUTHBEARER`). Donexto no pide la clave de
Yahoo. Ver [YAHOO_OAUTH.md](./YAHOO_OAUTH.md).

## Relación con el buzón

| Capa | Para qué |
|------|----------|
| Supabase Auth · Google / Azure / Apple | Cuenta Donexto (Crear cuenta) |
| Backend · `/auth/google/*` | Leer el buzón Gmail (Paso 2) |
| Backend · `/auth/yahoo/login` + callback | Entrar y leer el buzón Yahoo (OAuth + IMAP) |
