# Microsoft / Outlook / Hotmail / Microsoft 365 — Donexto

Donexto no pide la clave de Outlook. El usuario firma en
`login.microsoftonline.com`. El callback es Railway, no Supabase.

## Variables Railway

```text
AZURE_CLIENT_ID=<Application (client) ID>
AZURE_CLIENT_SECRET=<client secret>
AZURE_REDIRECT_URI=https://hms-ai-assistant-production.up.railway.app/auth/microsoft/callback
```

## App en Entra

1. https://entra.microsoft.com/ → App registrations → New registration
2. Name: **Donexto**
3. Supported accounts: **Accounts in any organizational directory and personal Microsoft accounts**
4. Redirect URI (Web): exactamente `AZURE_REDIRECT_URI`
5. Certificates & secrets → New client secret → pegar en Railway
6. API permissions → Microsoft Graph **delegated**:
   - `openid`
   - `email`
   - `profile`
   - `offline_access`
   - `User.Read`
   - `Mail.Read`
7. Grant admin consent solo si es un inquilino de trabajo. Cuentas personales consienten en el login.

## Flujo en la app

1. Correo `@outlook.com`, `@outlook.com.mx`, `@hotmail.com`, `@hotmail.com.mx`, `@live.com`, `@live.com.mx`, `@msn.com` o `@….onmicrosoft.com`
2. **Continuar** si ya hay cuenta Donexto → Microsoft
3. **Suscribirse** confirma el correo en Donexto y luego Microsoft (`intent=signup`)
4. Un correo Microsoft que no es usuario se queda en Donexto (igual que Mel Gibson en Yahoo)

Un dominio de empresa propio en Microsoft 365 (p. ej. `ana@empresa.mx`) no se detecta por el dominio: el usuario elige Outlook en el modal de buzón.
