# iCloud Mail en Donexto (IMAP, solo lectura)

Ruta paralela mientras Yahoo no entrega el alcance `mail-r`.
No activar `YAHOO_MAIL_READ_ENABLED`.

Donexto lee **solo** el correo que la persona autoriza. No marca leído,
no mueve y no borra.

Apple no da un OAuth de correo a esta app. El acceso es una
**contraseña específica de app** (no la contraseña del Apple ID).
Para crearla, la cuenta Apple tiene que tener la verificación en dos pasos.

## Servidor

| | |
|--|--|
| Host | `imap.mail.me.com` |
| Puerto | `993` SSL |
| Usuario | Correo completo: `@icloud.com`, `@me.com` o `@mac.com` |
| Secreto | Contraseña específica de app |
| Apertura | `EXAMINE` (`select` solo lectura) |
| Descarga | `BODY.PEEK` (no `BODY`, que marcaría leído) |

Código: `backend/app/services/imap_mail.py` (cliente común) y
`backend/app/services/icloud_imap.py` (iCloud). Yahoo sigue en el mismo
cliente IMAP con su config (`imap.mail.yahoo.com`, OAuth).

## Cómo conectar

1. En app.donexto.com escribe el correo iCloud y pulsa Continuar.
2. La pantalla explica, en el idioma de la app (es/en/fr/it/pt), cómo
   crear la contraseña en
   [account.apple.com](https://account.apple.com) → Inicio de sesión y
   seguridad → Contraseñas específicas de app.
3. Pegas el correo y esa contraseña. Donexto hace un LOGIN real contra
   iCloud y abre el INBOX en solo lectura.
4. Si el correo ya es la cuenta Donexto, tiene que coincidir. No se
   conecta otro buzón.
5. Tras verificar el correo Donexto (el enlace llega a iCloud; ábrelo
   en Mail de Apple), la app importa los últimos seis meses y arma casos.
   Spam, Papelera y Borradores no entran. El buzón de Apple no se modifica.

## Qué se guarda

- Cuenta `communication_accounts.provider = icloud`.
- Contraseña de app en `oauth_credentials.access_token`, cifrada con
  Fernet a partir de `OAUTH_ENCRYPTION_KEY` (la misma variable que Yahoo
  y Google). No va en texto claro. No se escribe en logs.
- Metadata: `auth=app_password`, `host=imap.mail.me.com`, `readonly=true`.
  La metadata no contiene la contraseña.

Desconectar (`POST /auth/icloud/disconnect`) borra las credenciales y
marca la cuenta como desconectada. Revocar en Apple es aparte: la
contraseña de app deja de servir aunque Donexto aún la tuviera.

## Errores

| Código | Qué ve la persona |
|--------|-------------------|
| `wrong_password` | La contraseña de app no sirvió |
| `app_password_required` | Pegó la contraseña del Apple ID, o Apple pidió contraseña de app |
| `two_factor_required` | Apple pide verificación en dos pasos o entrar por el navegador |
| `invalid_address` | No es `@icloud.com`, `@me.com` ni `@mac.com` |
| `email_mismatch` | El iCloud no es el correo de la cuenta Donexto |
| `network` | No hubo respuesta de `imap.mail.me.com:993` |

## API

- `POST /auth/icloud/connect` — público para el primer acceso (el IMAP
  es la prueba). Con sesión, el correo tiene que ser el de la cuenta.
- `GET /auth/icloud/status`
- `POST /auth/icloud/disconnect`
- Importación: `GET/POST /gmail/import/*` cuando `provider=icloud`

## Railway y Supabase

No hay variable nueva. No hay migración.

Hace falta la que ya existe:

- `OAUTH_ENCRYPTION_KEY` (32+ caracteres) en Railway.

Tablas que ya están: `communication_accounts` y `oauth_credentials`.
El proveedor `icloud` es texto libre; no cambia el esquema.
