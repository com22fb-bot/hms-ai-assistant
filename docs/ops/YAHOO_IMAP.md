# Yahoo Mail en Donexto (IMAP)

Hay dos caminos. El que lee el buzón **ahora** es la contraseña de app.
El OAuth se queda para cuando Yahoo entregue `mail-r`.
**No** activar `YAHOO_MAIL_READ_ENABLED`.

## Contraseña de app (ruta actual)

Aviso en la app: conexión directa con Yahoo mediante contraseña de app,
en espera de la autorización oficial. Solo lectura y revocable.

1. Seguridad de la cuenta Yahoo → Generar contraseña de app (hace falta 2FA).
2. En Donexto, correo Yahoo + esa contraseña.
3. LOGIN real contra `imap.mail.yahoo.com:993` SSL, INBOX con EXAMINE.
4. La contraseña se guarda cifrada con `OAUTH_ENCRYPTION_KEY`.
   `signup_via=yahoo_imap` no salta el correo de verificación de Donexto.
5. Desconectar borra la credencial. Revocar en Yahoo es aparte.

`POST /auth/yahoo/enter` y `POST /auth/yahoo/connect` siguen en 410:
esos endpoints no aceptan la contraseña de la cuenta. El camino nuevo es
`POST /auth/yahoo/imap/connect`.

## OAuth (cuando Yahoo autorice mail-r)

Ver [YAHOO_OAUTH.md](./YAHOO_OAUTH.md). El código de firma en Yahoo
sigue. Sin `mail-r` ese token no abre el inbox.

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
- Auth ahora: LOGIN con contraseña de app
- Auth más adelante: OAUTHBEARER si Yahoo entrega `mail-r`
- Backend: `POST /auth/yahoo/login` + `GET /auth/yahoo/callback`
- Importación: `GET/POST /gmail/import/*` (misma API que Gmail; rama IMAP si `provider=yahoo`)
