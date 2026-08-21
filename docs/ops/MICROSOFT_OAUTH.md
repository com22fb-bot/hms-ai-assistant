# Microsoft / Outlook / Hotmail / Microsoft 365 — Donexto

Donexto no pide la clave de Outlook. El usuario firma en
`login.microsoftonline.com`. El callback es Railway, no Supabase.

## Variables Railway

Después de crear la app en Entra, en el servicio
`hms-ai-assistant-production`:

```text
AZURE_CLIENT_ID=<Application (client) ID>
AZURE_CLIENT_SECRET=<client secret>
AZURE_REDIRECT_URI=https://hms-ai-assistant-production.up.railway.app/auth/microsoft/callback
```

Sin esas tres, `POST /auth/microsoft/login` responde 503 con instrucciones.
Railway publica `main`: hay que mergear el PR de Microsoft y dejar que
Railway redespliegue **antes** de probar Outlook en app.donexto.com.

## App en Entra

1. https://entra.microsoft.com/ → App registrations → New registration
2. Name: **Donexto**
3. Supported accounts: **Accounts in any organizational directory and personal Microsoft accounts** (cuentas personales de Outlook/Hotmail y Microsoft 365 de trabajo)
4. Redirect URI (plataforma **Web**): exactamente `AZURE_REDIRECT_URI`
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
2. **Continuar** solo si ya hay cuenta Donexto → Microsoft
3. **Suscribirse** pide confirmar el correo que se va a usar para el servicio Donexto. Todavía no sale de Donexto. Después firma en Microsoft (`intent=signup`)
4. Un correo Microsoft que no es usuario se queda en Donexto (igual que Mel Gibson en Yahoo)
5. Con `Mail.Read`, Donexto importa los últimos seis meses (inbox + enviados) igual que Gmail/Yahoo. Spam, papelera y borradores no entran.

Un dominio de empresa propio en Microsoft 365 (p. ej. `ana@empresa.mx`) no se detecta por el dominio: el usuario elige Outlook en el modal de buzón.
