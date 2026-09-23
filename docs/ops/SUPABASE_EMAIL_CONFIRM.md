# Supabase Auth — correo de confirmación Donexto

Si al crear cuenta ves “revisa tu correo” pero **no llega nada**:

## 1) Revisar en el panel Supabase

1. **Authentication → Providers → Email**
   - “Confirm email” activado → Supabase **debe** enviar el mail.
   - Si quieres entrar al instante en pruebas: desactiva “Confirm email”.
2. **Authentication → URL Configuration**
   - Site URL: `https://app.donexto.com`
   - Redirect URLs: incluye `https://app.donexto.com/**`, `https://app.donexto.com/` y las de www/apex del panel (`/admin`). Ver [ADMIN_EN_WWW.md](./ADMIN_EN_WWW.md).
3. **Project Settings → Auth → SMTP** (recomendado en prod)
   - El correo por defecto de Supabase (built-in) es limitado y a menudo cae en spam o no llega.
   - Configura SMTP propio (Resend, SendGrid, Brevo, etc.).

## 2) Bandeja del usuario

Revisar **spam / promociones** en `hmcelinfo@gmail.com` (o el correo usado).

## 3) App

Tras el alta, la UI muestra pantalla “Confirma tu correo” con:
- **Reenviar correo de confirmación**
- **Ya confirmé — Entrar**

No se puede spamear “Crear cuenta” otra vez en el mismo intento.

## 4) Reenvío localizado de Donexto

El endpoint `POST /identity/send-donexto-verify` arma el enlace con
`generate_link` tipo `magiclink` (no con `auth.resend` tipo `signup`) y
manda el asunto y el cuerpo del idioma de la interfaz por el relay del
backend. Un alta de Microsoft ya trae el correo confirmado por el
proveedor: pedir confirmación `signup` no genera correo. El enlace abre
la app con `donexto_verify=1` y el `token_hash` todavía sin usar. Deben
existir en Railway estas variables, o en su lugar `RESEND_API_KEY`:

- `SUPPORT_SMTP_HOST`
- `SUPPORT_SMTP_PORT`
- `SUPPORT_SMTP_USER`
- `SUPPORT_SMTP_PASSWORD`
- `SUPPORT_SMTP_FROM`

`SUPPORT_SMTP_FROM` en producción es `support@donexto.com`. Si el host SMTP
no está puesto y sí existe `RESEND_API_KEY`, el mismo correo sale por la API
de Resend.

Para Gmail y Google Workspace usa un relay autorizado por la cuenta, el puerto
`587` y STARTTLS. `SUPPORT_SMTP_FROM` debe ser una dirección permitida por ese
buzón o relay. La contraseña debe ser un secreto del proveedor (por ejemplo,
una contraseña de aplicación cuando la política de la cuenta lo requiera),
nunca la contraseña personal del usuario de Donexto.

El backend registra únicamente el tipo de error SMTP, host y puerto. No
registra credenciales ni devuelve secretos al frontend.

Si la cuenta ya tiene `app_metadata.donexto_verified` con
`donexto_verification_source=email`, `POST /identity/send-donexto-verify`
responde éxito y no manda otro correo. Un alta nueva de OAuth sigue
recibiendo un solo correo hasta que pulse Verificar.

## 5) Backfill único de cuentas viejas

Algunas cuentas que ya pulsaron Verificar (por ejemplo el primer alta con
Google) quedaron solo con `user_metadata.donexto_verified=true`. El login
en vivo no confía en ese campo. Migrarlas una vez, en Codespace, con la
service role ya configurada:

```bash
python scripts/backfill_donexto_verified_app_metadata.py
python scripts/backfill_donexto_verified_app_metadata.py --email hmcelinfo@gmail.com --apply
```

La primera corrida es dry-run. Revisa la lista: `user_metadata` lo puede
escribir el cliente, así que `--apply` es solo para cuentas que de verdad
completaron Verificar antes de pasar la prueba a `app_metadata`. No lo
programes. Volver a correrlo no reescribe a quien ya tiene la fuente
`email`, y `scripts/clean_oauth_donexto_verified.py` no les quita esa
bandera.

## 6) Clave de Railway para confirmar el enlace

`POST /identity/confirm-donexto` verifica el `token_hash` y después lee al
usuario con `auth.admin.get_user_by_id`. En el servicio `hms-ai-assistant`
la variable es `SUPABASE_SECRET_KEY`. Sirve la clave **secret** actual
(`sb_secret_…`) o el JWT legacy `service_role`. No hace falta cambiar la
que ya está: el envío del correo ya llama a la misma Admin API y responde
200. No pongas ahí la clave publishable ni el JWT `anon`; el proceso
arranca el rechazo en el log como `supabase_secret_key_cannot_admin` y
responde 500 antes de llamar a GoTrue.

No existe `SUPABASE_SERVICE_ROLE_KEY` en este repo. No la crees como
atajo: el cliente lee solo `SUPABASE_SECRET_KEY`.
