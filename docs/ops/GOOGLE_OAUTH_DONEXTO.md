# Google OAuth / Donexto — producción

## Valores canónicos (Railway + Google Cloud)

```text
GOOGLE_REDIRECT_URI=https://hms-ai-assistant-production.up.railway.app/auth/google/callback
FRONTEND_ORIGINS=https://app.donexto.com
```

Google Cloud → Cliente OAuth web:
- URI de redirección: la misma `GOOGLE_REDIRECT_URI` de arriba
- Consentimiento: nombre **Donexto**, inicio `https://app.donexto.com`
- Preferible estado **En producción** (sin lista de Test users)

## Comprobación sin secretos

```text
GET https://hms-ai-assistant-production.up.railway.app/env-status
```

Esperado:

```json
"oauth_shape": {
  "frontend_mentions_donexto": true,
  "redirect_is_railway_callback": true,
  "redirect_is_codespace": false,
  "ready_for_donexto_gmail": true
}
```

Si `redirect_is_codespace` es true, el Gmail button fallará con el mensaje de github.dev.

## Flujo app

1. Login Donexto en https://app.donexto.com  
2. Elegir Gmail → OAuth Google → cualquier Gmail (si app En producción)  
3. O Yahoo → correo + contraseña de aplicación IMAP  

## Marca

Producto: **Donexto** — *Lo que requiere atención en tu correo.*  
Proyecto GCP interno puede seguir llamándose “HMS AI Assistant”; el usuario ve **Donexto**.
