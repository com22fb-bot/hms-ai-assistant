# Yahoo Mail en Donexto (IMAP)

La identidad y la autorización son **OAuth**. Ver [YAHOO_OAUTH.md](./YAHOO_OAUTH.md).
Donexto no pide la clave de Yahoo.

IMAP solo se usa **después** de firmar en Yahoo, con el token OAuth
(`AUTHENTICATE OAUTHBEARER` en `imap.mail.yahoo.com:993`).

## Cómo conectar

1. En app.donexto.com: **Continuar con Yahoo**.
2. Firmas en el sitio de Yahoo.
3. Eso abre la app y, si Yahoo concedió `mail-r`, conecta el buzón.
4. Pantalla de **seis meses** → **Descargar y clasificar**.

No hay wizard de 16 dígitos, ni portal de Seguridad Yahoo, ni contraseña
de buzón en Donexto.

## Tras conectar

- Se guardan tokens OAuth cifrados (`OAUTH_ENCRYPTION_KEY` en Railway).
- Otros buzones del workspace pasan a inactivo.
- Donexto cuenta el INBOX y Enviados de los últimos **183 días** (seis meses).
- **Descargar y clasificar** importa esos mensajes y usa el mismo motor de casos que Gmail.
- Spam, Papelera y Borradores no se importan. El buzón de Yahoo no se modifica.

## Errores frecuentes

| Mensaje | Causa |
|---------|--------|
| Falta YAHOO_CLIENT_ID / SECRET / REDIRECT | App OAuth no creada o vars ausentes en Railway |
| Yahoo no aceptó la autorización OAuth | Token vencido o sin alcance `mail-r` |
| Error de red / timeout | Firewall o salida a `imap.mail.yahoo.com:993` bloqueada |
| Falta OAUTH_ENCRYPTION_KEY | Variable ausente en Railway |

## Servidor

- Host: `imap.mail.yahoo.com`
- Puerto: `993` SSL
- Auth: OAUTHBEARER (nunca LOGIN con clave)
- Backend: `POST /auth/yahoo/login` + `GET /auth/yahoo/callback`
- Importación: `GET/POST /gmail/import/*` (misma API que Gmail; rama IMAP si `provider=yahoo`)
