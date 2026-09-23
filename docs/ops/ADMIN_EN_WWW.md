# Admin en www.donexto.com

Héctor entra al panel en **https://www.donexto.com/admin** (también responde
**https://donexto.com/admin**). **https://app.donexto.com/admin** responde
**308** hacia www. La landing (`/`, términos, privacidad) sigue en Pages.

El Worker `donexto-app` no debe quedarse con todo el apex. Solo estos paths,
en www y en el apex:

- `/admin*`
- `/_next/*` (JS y CSS del panel)
- `/api/hms*` (proxy al backend)
- `/brand/*` (logo del login)
- `/favicon.ico` y `/manifest.webmanifest`

`npm run deploy` **no** escribe esas rutas. `frontend/wrangler.jsonc` no trae
`routes` a propósito: si las pones ahí, Wrangler puede quitar el dominio
`app.donexto.com`.

## 1. Rutas de Cloudflare (una vez)

En el Codespace, con un token que tenga **Zone Read** y **Workers Routes Edit**
en la zona `donexto.com`:

```bash
cd frontend
export CLOUDFLARE_API_TOKEN=...
node scripts/configure-admin-routes.mjs
```

Para ver la lista sin llamar a la API: `node scripts/configure-admin-routes.mjs --dry-run`.

El script solo **agrega** patrones que falten. No borra rutas ni el custom
domain de `app.donexto.com`.

A mano: Workers y Pages → `donexto-app` → Settings → Domains & Routes → Add route.
Zona `donexto.com`, script `donexto-app`, los mismos patrones. Workers gana
sobre Pages en el path que coincide. `/` se queda en el proyecto Pages `donexto`.

Si la API rechaza la ruta porque Pages ya es dueño del hostname, no pongas
`donexto.com/*` en el Worker. Abre un ticket o usa el dashboard: un route
`www.donexto.com/admin*` es más específico que el custom domain de Pages.

## 2. Supabase → Authentication → URL Configuration

Site URL se queda **`https://app.donexto.com`** (el correo de la app de usuarios
sigue cayendo ahí).

Agrega a **Redirect URLs** (no quites las de `app` ni localhost):

```text
https://www.donexto.com/admin
https://www.donexto.com/admin/**
https://donexto.com/admin
https://donexto.com/admin/**
https://www.donexto.com/**
https://donexto.com/**
```

Sin eso, Google / Azure / magic link / restablecer contraseña desde el panel
en www fallan en Supabase. El código no puede escribir el dashboard.

Proyecto: `tgirnpystoydvbxlvlzz`
https://supabase.com/dashboard/project/tgirnpystoydvbxlvlzz/auth/url-configuration

## 3. Redeploy

1. Frontend (Codespace): `cd frontend && npm run deploy`
   (`CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID`).
2. Backend en Railway, para que CORS y `return_to` de Yahoo/Microsoft acepten
   www y el apex. El código los suma solo si `FRONTEND_ORIGINS` ya incluye
   `https://app.donexto.com`. Igual conviene dejarlos explícitos:

```text
FRONTEND_ORIGINS=https://app.donexto.com,https://www.donexto.com,https://donexto.com
```

Reinicia el servicio después de guardar.

## 4. Cómo verificar

- `https://www.donexto.com/admin` muestra el login del panel (español, sin
  selector de idioma), no la landing.
- `https://donexto.com/admin` igual.
- `curl -sI https://app.donexto.com/admin` → `308` y
  `Location: https://www.donexto.com/admin`.
- `https://www.donexto.com/` y `https://donexto.com/` siguen siendo la landing.
- `https://app.donexto.com/` sigue siendo el login de la app (varios idiomas).
- Entrar con correo en www/admin y abrir Resumen. Yahoo/Microsoft en el panel
  solo después del redeploy del backend.

El botón **App** del panel abre `https://app.donexto.com` con navegación
completa, para no cargar `/` de la landing dentro del router de Next.
