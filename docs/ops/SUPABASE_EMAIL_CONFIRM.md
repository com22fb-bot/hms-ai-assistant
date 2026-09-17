# Supabase Auth — correo de confirmación Donexto

Si al crear cuenta ves “revisa tu correo” pero **no llega nada**:

## 1) Revisar en el panel Supabase

1. **Authentication → Providers → Email**
   - “Confirm email” activado → Supabase **debe** enviar el mail.
   - Si quieres entrar al instante en pruebas: desactiva “Confirm email”.
2. **Authentication → URL Configuration**
   - Site URL: `https://app.donexto.com`
   - Redirect URLs: incluye `https://app.donexto.com/**` y `https://app.donexto.com/`
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

El endpoint `POST /identity/send-donexto-verify` genera el enlace con
Supabase y envía el asunto y cuerpo localizados mediante el relay SMTP del
backend. Deben existir en Railway estas variables:

- `SUPPORT_SMTP_HOST`
- `SUPPORT_SMTP_PORT`
- `SUPPORT_SMTP_USER`
- `SUPPORT_SMTP_PASSWORD`
- `SUPPORT_SMTP_FROM`

Para Gmail y Google Workspace usa el host SMTP autorizado por la cuenta y el
puerto `587` con STARTTLS. `SUPPORT_SMTP_FROM` debe ser una dirección permitida
por ese buzón o relay. La contraseña debe ser un secreto del proveedor (por
ejemplo, una contraseña de aplicación cuando la política de la cuenta lo
requiera), nunca la contraseña personal del usuario de Donexto.

El backend registra únicamente el tipo de error SMTP, host y puerto. No
registra credenciales ni devuelve secretos al frontend.
