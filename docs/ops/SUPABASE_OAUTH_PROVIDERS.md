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

### Yahoo (no es nativo)

Supabase Auth **no incluye** `provider=yahoo`. Por eso
`{"msg":"Unsupported provider: Provider yahoo could not be found"}`.

Hay que crear un proveedor **custom**:

1. [Yahoo Developer](https://developer.yahoo.com/) → app OAuth2 / OpenID.
   Redirect URI = callback de abajo.
2. Supabase → **Authentication** → **Sign In / Providers** → **New Provider**
   → **Manual configuration (OAuth2)**.
3. Identifier: `custom:yahoo`
4. Client ID y Client Secret de Yahoo.
5. URLs:
   - Authorization: `https://api.login.yahoo.com/oauth2/request_auth`
   - Token: `https://api.login.yahoo.com/oauth2/get_token`
   - UserInfo: `https://api.login.yahoo.com/openid/v1/userinfo`
6. Scopes: `openid email profile`
7. Callback (el de Supabase, no el de la app):

```text
https://tgirnpystoydvbxlvlzz.supabase.co/auth/v1/callback
```

La app llama `signInWithOAuth({ provider: 'custom:yahoo' })`.
Entrar con Yahoo **no** envía un enlace mágico: te lleva a login.yahoo.com.
El mail de Donexto es solo al **alta**, una vez.

Si el proveedor no está creado, la UI explica estos pasos (ya no muestra el JSON).

## Relación con el buzón

| Capa | Para qué |
|------|----------|
| Supabase Auth · Google / Azure / Apple | Cuenta Donexto (Crear cuenta) |
| Backend · `/auth/google/*` | Leer el buzón Gmail (Paso 2) |
| IMAP Yahoo | Leer el buzón Yahoo (Paso 2) |
