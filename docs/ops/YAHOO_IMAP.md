# Yahoo Mail en Donexto

## Cómo conectar

1. Crear cuenta Donexto (enlace al mismo Yahoo).
2. Verificar el correo Donexto.
3. Conectar buzón → **Yahoo** con **contraseña de aplicación** IMAP (no la de mail.yahoo.com).
4. Pantalla de **seis meses** → **Descargar y clasificar** (mismas barras que Gmail).

### Generar app password

1. https://login.yahoo.com/account/security  
2. Verificación en 2 pasos (obligatoria en la mayoría).  
3. Conexiones externas → Crear contraseña de aplicación.  
4. Nombre: `Donexto` → copiar código (~16 caracteres).  
5. Pegarlo en Donexto al autorizar el buzón (espacios se ignoran).

## Tras conectar

- Se guardan credenciales cifradas (`OAUTH_ENCRYPTION_KEY` en Railway).
- Otros buzones del workspace pasan a inactivo.
- Donexto cuenta el INBOX y Enviados de los últimos **183 días** (seis meses).
- **Descargar y clasificar** importa esos mensajes y usa el mismo motor de casos que Gmail.
- Spam, Papelera y Borradores no se importan. El buzón de Yahoo no se modifica.

## Errores frecuentes

| Mensaje | Causa |
|---------|--------|
| Yahoo rechazó… | Contraseña normal o app password vieja |
| Demasiado corta | No se pegó el código de aplicación |
| Error de red / timeout | Firewall o salida a `imap.mail.yahoo.com:993` bloqueada |
| Falta OAUTH_ENCRYPTION_KEY | Variable ausente en Railway |

## Servidor

- Host: `imap.mail.yahoo.com`
- Puerto: `993` SSL
- Backend: `POST /auth/yahoo/connect`
- Importación: `GET/POST /gmail/import/*` (misma API que Gmail; rama IMAP si `provider=yahoo`)
