# Landing Donexto → donexto.com (Cloudflare Pages)

Sitio estático: `landing/donexto/`

Archivos a subir:

- `index.html`
- `styles.css`
- `app.js`
- `favicon.svg`
- `promo.mp4` (video promocional)

## Ver en tu PC (ya)

```powershell
cd C:\Users\hsalc\hms-ai-assistant\landing\donexto
python -m http.server 5500
```

Abre: http://127.0.0.1:5500

O doble clic en `index.html` (el video puede fallar por file:// en algunos navegadores; el servidor local es más fiable).

## Publicar en donexto.com

1. [dash.cloudflare.com](https://dash.cloudflare.com) → **Workers & Pages**
2. Proyecto Pages de la landing (o **Create** → **Upload assets**)
3. Sube **toda** la carpeta `landing/donexto/` (incluye `promo.mp4` ~2.6 MB)
4. **Custom domains**: `donexto.com` y `www.donexto.com`

Alternativa Wrangler (si tienes token):

```bash
cd landing/donexto
npx wrangler pages deploy . --project-name=donexto
```

## Contenido de la página

- Hero plan maestro / promesa hogar
- Video `promo.mp4`
- Niveles N1 / N2 / N3 (mercado EE. UU.)
- Cómo funciona (login ≠ buzón)
- Qué hay en la app (home atención)
- CTA → https://app.donexto.com
- ES/EN, redes, mailto hola@ / hello@

## Checklist post-deploy

- [ ] https://donexto.com carga
- [ ] Video se reproduce
- [ ] EN/ES cambia textos
- [ ] app.donexto.com abre la app
- [ ] Formulario mailto funciona
