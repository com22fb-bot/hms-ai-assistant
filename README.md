# Donexto

Capa de atención sobre el correo personal. El usuario entra en
[app.donexto.com](https://app.donexto.com). La landing está en
[www.donexto.com](https://www.donexto.com).

## Qué corre dónde

| Pieza | Dónde |
| --- | --- |
| App (Next.js) | Cloudflare Worker `donexto-app` |
| Landing | Cloudflare Pages `donexto` (`--branch main`) |
| API (FastAPI, OAuth, importar correo) | Railway `hms-ai-assistant-production` |
| Auth y datos | Supabase |

No se usa Vercel. El código se trabaja en GitHub Codespace, no en la laptop Windows.

## Servicios activos

Yahoo (identidad; lectura de buzón pendiente de `mail-r`) y Outlook/Hotmail/Live/MSN/Microsoft 365. Gmail e iCloud: acceso en revisión.

## Deploy

```bash
# App Worker (Codespace)
cd /workspaces/hms-ai-assistant
git checkout main && git pull origin main
cd frontend
export CLOUDFLARE_API_TOKEN='…'
npm run deploy
```

```bash
# Landing Pages (producción = rama main)
cd /workspaces/hms-ai-assistant/landing/donexto
bash deploy-production.sh
```

Railway publica `main` solo.

## Repo

Producto: `backend/`, `frontend/`, `landing/`, `supabase/`.  
Contacto: support@donexto.com
