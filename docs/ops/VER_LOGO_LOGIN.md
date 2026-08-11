# Por qué no ves el logo en app.donexto.com

El código y las imágenes **están en tu disco / repo de trabajo local**.  
La app pública **app.donexto.com** solo cambia cuando haces **deploy** del Worker `donexto-app`.

## Ver YA en tu PC

```powershell
cd C:\Users\hsalc\hms-ai-assistant\frontend
npm run dev
```

Abre http://localhost:3000 y haz **Ctrl+Shift+R**.

Debes ver:
- Fondo oscuro teal
- Logo 3D Donexto grande
- Texto **Do Next To…**
- Formulario de cuenta Donexto

## Publicar en app.donexto.com (Codespace)

```bash
cd /workspaces/hms-ai-assistant
# si hace falta: git pull / commit de brand + LoginScreen

export CLOUDFLARE_API_TOKEN="tu_token"
cd frontend
# variables NEXT_PUBLIC_SUPABASE_* como siempre
npm run deploy
```

Luego **Ctrl+Shift+R** en https://app.donexto.com

## Si sigue “la interfaz fea”

1. ¿Estás en **app.donexto.com** (producción vieja) o en **localhost**?  
2. Prueba ventana de incógnito.  
3. Confirma que existe:  
   `frontend/public/brand/donexto-logo-official.png`
