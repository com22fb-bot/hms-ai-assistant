# Google OAuth para Donexto (sin lista de Test users)

Google **no permite** omitir Test users desde código mientras la app OAuth está en **Prueba / Testing**.

## Objetivo

Cualquier cuenta Donexto (p. ej. las 2 de login) debe poder conectar **cualquier Gmail** sin registrar cada dirección en Google Cloud.

## Pasos en Google Cloud Console

1. Proyecto OAuth de Donexto → **APIs y servicios** → **Pantalla de consentimiento de OAuth**.
2. **Nombre de la app:** `Donexto` (no HMS, no github.dev).
3. **Página de inicio de la aplicación:** `https://app.donexto.com`
4. **Dominio autorizado:** `donexto.com`
5. **Estado de publicación:** cambia de **Prueba** a **En producción**.
6. **Credenciales → Cliente OAuth web**  
   - URI de redirección autorizada (Railway), por ejemplo:  
     `https://hms-ai-assistant-production.up.railway.app/auth/google/callback`  
   - Quita URIs de `*.app.github.dev` si solo usas producción (o déjalas solo para desarrollo).
7. En **Railway**:  
   `GOOGLE_REDIRECT_URI` = ese mismo callback de Railway  
   `FRONTEND_ORIGINS=https://app.donexto.com`

## Notas

- Tras **En producción**, Google deja de exigir la lista de Test users.
- Los scopes de Gmail son **restringidos**: puede aparecer “app no verificada”. El usuario puede avanzar con *Avanzado → Ir a Donexto* hasta completar la verificación formal de Google (proceso aparte, puede tardar días).
- **Yahoo** no usa Google OAuth: correo + contraseña de aplicación IMAP en Donexto.
- Abrir siempre [https://app.donexto.com](https://app.donexto.com), no la preview de Codespace.

## Yahoo

No requiere usuarios de prueba ni Google Cloud.
