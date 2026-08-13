# Google en Supabase Auth (Crear cuenta → Gmail)

Guía completa (Google + Azure/Microsoft + Apple): [SUPABASE_OAUTH_PROVIDERS.md](./SUPABASE_OAUTH_PROVIDERS.md).

Esto es el **login de identidad** de Donexto con Google (`signInWithOAuth({ provider: 'google' })`).
No sustituye la conexión del buzón Gmail (lectura del correo), que sigue en el Paso 2
(`POST /auth/google/start`). Ver [GOOGLE_OAUTH_DONEXTO.md](./GOOGLE_OAUTH_DONEXTO.md).

No hay secretos en este documento.

Rutas del dashboard verificadas en docs oficiales y código de Studio (agosto 2026).
El menú ya **no** es “Authentication → Providers”: es **Authentication → Sign In / Providers**.

## Qué habilitar

1. **Supabase Dashboard**  
   Entra a https://supabase.com/dashboard → proyecto Donexto
   (`tgirnpystoydvbxlvlzz`, el de `app.donexto.com`).

2. **Authentication → Sign In / Providers → Google**  
   Barra izquierda del proyecto: **Authentication** (si está colapsada, el icono de candado/usuarios).
   En el submenú, grupo **Configuration**, ítem **Sign In / Providers** (no un ítem suelto “Providers”).
   Pestaña **Supabase Auth** (no **Third-Party Auth**).
   Abre **Google**. Interruptor **Enable Sign in with Google**.
   Pega **Client IDs** y **Client Secret (for OAuth)** del cliente OAuth de Google Cloud
   (tipo Web; el mismo de Gmail si el tipo de cliente lo permite).

   Enlace directo:
   https://supabase.com/dashboard/project/tgirnpystoydvbxlvlzz/auth/providers?provider=Google

3. **Callback de Supabase en Google Cloud**  
   En el cliente OAuth (tipo Web) agrega **Authorized redirect URIs**:

   ```text
   https://tgirnpystoydvbxlvlzz.supabase.co/auth/v1/callback
   ```

   Ese host es el de `NEXT_PUBLIC_SUPABASE_URL` en producción.
   **No quites** el callback de Railway del buzón Gmail
   (`https://hms-ai-assistant-production.up.railway.app/auth/google/callback`);
   son redirecciones distintas.

4. **Site URL** en **Authentication → URL Configuration**:

   ```text
   https://app.donexto.com
   ```

   Redirect URLs: `https://app.donexto.com/`, `https://app.donexto.com/**` y, en local,
   `http://localhost:3000/` (o `http://localhost:3000/**`).

## Si no ves “Providers”

1. Pega el enlace directo de Google (arriba). Las rutas viejas
   `/project/…/auth/settings` y `/project/…/settings/auth` redirigen a `/auth/providers`.
2. En el submenú de Authentication busca **Sign In / Providers** (grupo Configuration).
3. Engranaje **Project Settings**: si aparece Authentication con flecha, abre ahí;
   o escribe en la barra del navegador `…/settings/auth`.

## Flujo en la app

1. Login → **Crear cuenta** → **Gmail**.
2. Google muestra consentimiento; Supabase crea la sesión Donexto.
3. `redirectTo` es el origin actual + `/` (prod: `https://app.donexto.com/`).
4. Si aún no hay buzón conectado, el Paso 2 / `MailboxConnectModal` pide
   autorizar **lectura de Gmail** (OAuth de producto, no el de Auth).

## Error “provider is not enabled”

El proveedor Google no está activo en Supabase Auth, o el Client ID no coincide.
La UI traduce ese error; no es un fallo del botón.

## Relación con Gmail (buzón)

| Capa | Dónde | Para qué |
|------|--------|----------|
| Supabase Auth · Google | Este doc | Cuenta Donexto (Crear cuenta) |
| Backend · `/auth/google/*` | `GOOGLE_OAUTH_DONEXTO.md` | Leer el buzón Gmail |
