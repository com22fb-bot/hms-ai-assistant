# Landing Donexto -> donexto.com (Cloudflare Pages)

Sitio estatico: landing/donexto/

## NO subir promo.mp4 viejo
El clip de ~10s decia "Donextu". Esta fuera de index.html.
Historia de 40 s = boton "Reproducir historia" (sin audio hasta que Hector grabe).
Guion: GUION-40S-ES-MX.txt
DNS apex: CLOUDFLARE-DNS-APEX.txt
Fotos JPEG: brand-escritorio.jpg, brand-youtube.jpg, brand-logo-3d.jpg (placa 3D header)
Colores: cian #24c8ca + magenta #d63d8e (logo 3D Do Next To…)

## Codespace (deploy, no desde la laptop)

1. Copiar el zip a Codespace y:
```bash
cd /workspaces/hms-ai-assistant
unzip -o donexto-p01c-brand-v3.zip
rm -f landing/donexto/promo.mp4
cd landing/donexto
ls -l brand-escritorio.jpg brand-logo-3d.jpg brand-youtube.jpg
# Si alguno falta o es 0 bytes: NO desplegar.
npx wrangler pages deploy . --project-name=donexto --commit-dirty=true
```
Verificar https://www.donexto.com/ Y https://donexto.com/ (apex).
2. En el dashboard: Pages -> donexto -> Deployments -> Promote to production
   (www home no cambia hasta Promote)

## Apex = landing
Custom domains en Pages proyecto donexto: donexto.com Y www.donexto.com
app.donexto.com se queda en el Worker. Quitar apex del Worker si esta ahi.
Ver CLOUDFLARE-DNS-APEX.txt

## Contacto
support@donexto.com (oficial). hello@ / hola@ no son el canal primario.

## Ver en PC
```powershell
cd C:\Users\hsalc\hms-ai-assistant\landing\donexto
python -m http.server 5500
```
http://127.0.0.1:5500  -> Reproducir historia
