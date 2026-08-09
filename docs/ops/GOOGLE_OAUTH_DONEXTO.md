# Google OAuth / Donexto — producción

## Valores canónicos (Railway + Google Cloud)

```text
GOOGLE_REDIRECT_URI=https://hms-ai-assistant-production.up.railway.app/auth/google/callback
FRONTEND_ORIGINS=https://app.donexto.com
OAUTH_ENCRYPTION_KEY=<secreto >= 32 caracteres, ver abajo>
```

Google Cloud → Cliente OAuth web:
- URI de redirección: la misma `GOOGLE_REDIRECT_URI` de arriba
- Consentimiento: nombre **Donexto**, inicio `https://app.donexto.com`
- Preferible estado **En producción** (sin lista de Test users)

## OAUTH_ENCRYPTION_KEY (obligatoria)

Cifra tokens de Gmail y contraseñas de aplicación Yahoo antes de guardar en Supabase.

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Pega el resultado en Railway Variables del API como `OAUTH_ENCRYPTION_KEY`.  
Redeploy. **No cambies esta clave** después de conectar buzones.

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
  "encryption_key_present": true,
  "ready_for_donexto_gmail": true
}
```

## Flujo app

1. Login Donexto en https://app.donexto.com  
2. Elegir Gmail → OAuth Google → cualquier Gmail (si app En producción)  
3. O Yahoo → correo + contraseña de aplicación IMAP  

## Marca

Producto: **Donexto** — *Lo que requiere atención en tu correo.*  
Proyecto GCP interno puede seguir llamándose “HMS AI Assistant”; el usuario ve **Donexto**.
