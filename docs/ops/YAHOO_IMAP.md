# Yahoo Mail en Donexto

## Cómo conectar

1. Login Donexto (no es la contraseña de Yahoo).
2. Conectar buzón → **Yahoo**.
3. Correo: `tucorreo@yahoo.com` / `@ymail.com` / `@rocketmail.com`.
4. Contraseña: **contraseña de aplicación** (IMAP), no la de mail.yahoo.com.

### Generar app password

1. https://login.yahoo.com/account/security  
2. Verificación en 2 pasos (obligatoria en la mayoría).  
3. Conexiones externas → Crear contraseña de aplicación.  
4. Nombre: `Donexto` → copiar código (~16 caracteres).  
5. Pegarlo en Donexto (espacios se ignoran).

## Tras conectar

- Se guardan credenciales cifradas (`OAUTH_ENCRYPTION_KEY` en Railway).  
- Otros buzones del workspace pasan a inactivo.  
- “Cargar correos” abre la bandeja **en vivo** (IMAP).  
- Los cuadros de **casos** pueden seguir en 0 hasta que exista import/clasificación (hoy es fuerte en Gmail).

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
- Backend: `POST /auth/yahoo/connect`, lectura vía `GET /gmail/messages` si provider=yahoo
