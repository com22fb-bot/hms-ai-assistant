# HMS AI Assistant 4.5 — Autenticación real con cualquier correo

Esta versión sustituye el login de demostración por Supabase Auth.

## Funciones

- Registro con Gmail, Outlook, Hotmail, Yahoo o correo empresarial.
- Inicio de sesión real con correo y contraseña.
- Confirmación por correo según la configuración de Supabase.
- Recuperación de contraseña.
- Sesión persistente y cierre de sesión.
- Creación automática del perfil mediante la migración existente.
- La cuenta HMS queda separada de la conexión del buzón Gmail.

## Variables públicas necesarias

```env
NEXT_PUBLIC_SUPABASE_URL=https://TU_PROYECTO.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
```

Nunca pongas `SUPABASE_SECRET_KEY` en el frontend.
