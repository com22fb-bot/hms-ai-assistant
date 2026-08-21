# Yahoo OAuth en Donexto

Donexto **nunca** pide la contraseña de Yahoo, Gmail ni de ningún buzón.
El usuario firma en el sitio de Yahoo, igual que Gmail firma en Google.

**Tener un correo Yahoo no da acceso a Donexto.** El botón de Yahoo solo
identifica a quien ya es usuario. Si Yahoo confirma un correo que no está
en Auth, no hay sesión: la app abre **Crear cuenta**.

## Flujo

1. En `app.donexto.com`: **Continuar con Yahoo** (`intent=login`) o
   **Crear cuenta con Yahoo** (`intent=signup`).
2. El backend responde `POST /auth/yahoo/login` con `authorization_url`.
3. El navegador abre `https://api.login.yahoo.com/oauth2/request_auth`.
4. Yahoo redirige a Railway: `GET /auth/yahoo/callback`.
5. Donexto intercambia el código y lee el correo en userinfo.
6. Si `intent=login` y el correo **no** existe en Auth: redirect a
   `https://app.donexto.com/?donexto=signup&reason=no_account` **sin tokens**.
7. Si el correo ya existe, o si `intent=signup`: mint de sesión Auth y
   redirect a `https://app.donexto.com/#access_token=…`.

## App en Yahoo (Héctor)

1. Crear la app en <https://developer.yahoo.com/apps/>.
2. Redirect URI (exacto):

   ```text
   https://hms-ai-assistant-production.up.railway.app/auth/yahoo/callback
   ```

3. Alcances básicos: `openid`, `email`, `profile`.
4. Lectura de correo (`mail-r`) **no es self-serve**. Hay que pedirla en
   <https://senders.yahooinc.com/developer/developer-access/>.
   Sin `mail-r` el usuario que **ya tiene cuenta Donexto** entra, pero IMAP
   no lee el buzón.

## Variables en Railway

```text
YAHOO_CLIENT_ID=
YAHOO_CLIENT_SECRET=
YAHOO_REDIRECT_URI=https://hms-ai-assistant-production.up.railway.app/auth/yahoo/callback
YAHOO_OAUTH_SCOPES=openid email profile
```

No pongas `mail-r` hasta que Yahoo lo apruebe en
<https://senders.yahooinc.com/developer/developer-access/>.
Si lo pides sin aprobación, Yahoo responde `invalid_scope`.

Sin esas variables, `POST /auth/yahoo/login` responde **503** con el enlace
de developer. No desplegar el Worker de esta rama hasta pegarlas.

## IMAP

Lectura: `imap.mail.yahoo.com:993` con `AUTHENTICATE OAUTHBEARER` y el
access token. **No** se guarda ni se pide una clave de Yahoo.

`POST /auth/yahoo/enter` y `POST /auth/yahoo/connect` (el modelo de clave)
responden **410**.

## Endpoints

| Ruta | Auth | Qué hace |
|------|------|----------|
| `POST /auth/yahoo/login` | público | URL para firmar en Yahoo (`intent` login o signup) |
| `GET /auth/yahoo/callback` | público | Identidad Yahoo; sesión solo si ya hay cuenta o es alta |
| `POST /auth/yahoo/enter` | público | 410: no acepta clave |
| `POST /auth/yahoo/connect` | sesión | 410: reconectar es firmar otra vez |
