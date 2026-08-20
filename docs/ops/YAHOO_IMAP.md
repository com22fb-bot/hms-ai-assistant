# Yahoo Mail en Donexto

## Cómo conectar

1. En app.donexto.com: **Continuar con Yahoo**.
2. Correo Yahoo + **la misma clave con la que entra a Yahoo**.
3. Eso abre la app y conecta el buzón. **No hay alta de usuario Donexto** ni enlace de confirmación.
4. Pantalla de **seis meses** → **Descargar y clasificar**.

No hay wizard de 16 dígitos, ni portal de Seguridad Yahoo, ni verificación en dos pasos dentro de Donexto.

## Tras conectar

- Se guardan credenciales cifradas (`OAUTH_ENCRYPTION_KEY` en Railway).
- Otros buzones del workspace pasan a inactivo.
- Donexto cuenta el INBOX y Enviados de los últimos **183 días** (seis meses).
- **Descargar y clasificar** importa esos mensajes y usa el mismo motor de casos que Gmail.
- Spam, Papelera y Borradores no se importan. El buzón de Yahoo no se modifica.

## Errores frecuentes

| Mensaje | Causa |
|---------|--------|
| Yahoo no aceptó esa clave | Correo o clave distintos a los de Yahoo |
| Demasiado corta | La clave no se escribió completa |
| Error de red / timeout | Firewall o salida a `imap.mail.yahoo.com:993` bloqueada |
| Falta OAUTH_ENCRYPTION_KEY | Variable ausente en Railway |

## Servidor

- Host: `imap.mail.yahoo.com`
- Puerto: `993` SSL
- Backend: `POST /auth/yahoo/enter` (público: login + buzón) y `POST /auth/yahoo/connect` (reconectar ya logueado)
- Importación: `GET/POST /gmail/import/*` (misma API que Gmail; rama IMAP si `provider=yahoo`)
