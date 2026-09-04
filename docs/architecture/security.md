# Seguridad de autenticación — Donexto / HMS AI Assistant

Este documento describe el modelo de seguridad del flujo de identidad (cuenta Donexto) frente al buzón (lectura de correo), qué datos son confiables y qué queda pendiente.

## Modelo mental: identidad vs buzón

| Concepto | Qué es | Dónde vive |
|----------|--------|------------|
| **Cuenta Donexto** | Identidad del usuario en la app (email + sesión Supabase) | Supabase Auth + tabla `profiles` |
| **Verificación Donexto** (`donexto_verified`) | Prueba de que el usuario controla el correo de la cuenta | `app_metadata` (solo service role) |
| **Buzón conectado** | Credenciales OAuth/IMAP para leer correo del workspace | `communication_accounts` (cifrado) |
| **mailbox_verified / mailbox_ok** | *(P2 — fuera de este PR)* | Pendiente |

La verificación Donexto **no** es lo mismo que conectar el buzón. Un usuario puede tener cuenta verificada sin buzón conectado.

## Fuentes de confianza

### Confiable (backend / service role)

- `app_metadata.donexto_verified` — escrito solo por el backend vía Admin API
- `email_confirmed_at` en Supabase Auth — magic link / confirmación de signup
- Identidades OAuth en `identities` / `app_metadata.providers` (Google, Azure, Yahoo vía callback)
- Tokens de sesión Supabase validados con `auth.get_user(access_token)`
- OAuth state almacenado server-side (`oauth_storage`)

### No confiable para autorización

- `user_metadata` — el cliente puede llamar `supabase.auth.updateUser({ data: … })`
- Query params del frontend (`?donexto_verify=1`) — solo disparan una llamada al backend; no prueban nada por sí solos
- Campo `exists` en respuestas públicas — eliminado; la ruta se infiere de `next`

## Flujos

### 1. Email + contraseña / magic link Donexto

1. Usuario crea cuenta o recibe OTP/magic link con `?donexto_verify=1`.
2. Supabase marca `email_confirmed_at` al hacer clic.
3. Frontend llama `POST /identity/confirm-donexto` con Bearer token.
4. Backend comprueba `email_confirmed_at` o identidad OAuth y escribe `app_metadata.donexto_verified=true`.
5. Middleware bloquea rutas protegidas si no hay verificación (salvo `/identity/me` y `/identity/confirm-donexto`).

### 2. OAuth identidad (Yahoo / Microsoft vía backend)

1. `POST /auth/yahoo/login` o `/auth/microsoft/login` con `return_to` sanitizado.
2. Callback intercambia código, crea/actualiza usuario Auth con Admin API.
3. `donexto_verified` se escribe en **`app_metadata`**, no en `user_metadata`.
4. Redirect al frontend con tokens en fragmento URL (ver riesgo P2.1 abajo).

### 3. OAuth identidad (Google / Azure vía Supabase)

1. `supabase.auth.signInWithOAuth` en el frontend.
2. Tras sesión, frontend llama `POST /identity/confirm-donexto`.
3. Backend detecta identidad OAuth y marca `app_metadata`.

### 4. Gate de login (`POST /auth/login/resolve`)

- Endpoint **público** con rate limiting por IP (30 req/min).
- No expone booleano `exists`; el cliente deriva si hay cuenta existente de `next` (`yahoo_oauth`, `google_oauth`, etc.).
- Sigue siendo posible inferir existencia vía `next`; el rate limit reduce enumeración masiva.

## Redirect OAuth (`sanitize_return_to`)

Post-callback, el backend redirige a `return_to`. Solo se aceptan orígenes **exactos** de `FRONTEND_ORIGINS` (p. ej. `https://app.donexto.com`, `http://localhost:3000`).

**Corregido:** ya no se acepta cualquier host que termine en `donexto.com` (p. ej. `https://falsodonexto.com`).

Implementación: `backend/app/security/redirect.py`.

## Tokens en fragmento URL (`#access_token=…`)

Tras Yahoo/Microsoft OAuth, el backend redirige a:

```text
https://app.donexto.com/#access_token=…&refresh_token=…&type=magiclink
```

### Riesgo

- El fragmento **no** se envía al servidor en navegación normal, pero:
  - Puede quedar en historial del navegador.
  - Scripts en la misma página (XSS) pueden leer `location.hash`.
  - Extensiones maliciosas pueden observarlo.
  - Referrer no incluye hash, pero logs locales sí.

### Mitigación actual

- Redirect limitado a orígenes allowlist.
- Tokens son de sesión Supabase de corta duración relativa al refresh.
- HTTPS obligatorio en producción.

### Pendiente P2.1 — PKCE + cookies HttpOnly

**TODO:** Sustituir el paso de tokens por fragmento con:

1. Intercambio one-time code server-side (`POST /auth/session/exchange`).
2. Cookie `HttpOnly; Secure; SameSite=Lax` para la sesión.
3. PKCE en flujos OAuth donde el proveedor lo soporte.

Hasta entonces, documentado como deuda conocida; no bloquea el hardening de `donexto_verified` ni redirects.

## Variables y secretos

| Variable | Uso | Expuesta al cliente |
|----------|-----|---------------------|
| `SUPABASE_SECRET_KEY` | Admin API, validación server-side | **Nunca** |
| `OAUTH_ENCRYPTION_KEY` | Cifrado tokens de buzón | **Nunca** |
| `FRONTEND_ORIGINS` | Allowlist redirects CORS | Lista de URLs, no secreto |
| `NEXT_PUBLIC_*` | URL API frontend | Sí (público) |

## Archivos relevantes

- `backend/app/security/redirect.py` — allowlist `return_to`
- `backend/app/security/donexto_verified.py` — lectura/escritura confiable
- `backend/app/security/identity.py` — autenticación Bearer + contexto workspace
- `backend/app/api/identity.py` — `/me`, `/confirm-donexto`
- `backend/app/middleware/authentication_context.py` — gate `donexto_verified`
- `backend/app/api/login_resolve.py` — gate email-first + rate limit
- `frontend/hooks/useAppAuth.ts` — ya no escribe `user_metadata.donexto_verified`

## Decisiones de diseño (PR auth-hardening)

1. **`donexto_verified` en `app_metadata`**, no `user_metadata`, porque Supabase permite al usuario editar `user_metadata` desde el cliente.
2. **Confirmación centralizada** en `POST /identity/confirm-donexto` en lugar de `updateUser` en el navegador.
3. **Middleware** rechaza operaciones HMS si falta verificación (excepto endpoints de identidad necesarios para completarla).
4. **`exists` eliminado** del resolve; rate limit añadido como defensa pragmática.
5. **PKCE/cookies** documentado como P2.1; fuera del alcance de este PR.
