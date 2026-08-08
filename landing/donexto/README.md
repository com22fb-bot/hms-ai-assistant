# Landing Donexto → Cloudflare Pages

Sitio estático en `landing/donexto/`.

## Publicar (panel Cloudflare)

1. Entra a [dash.cloudflare.com](https://dash.cloudflare.com).
2. **Workers & Pages** → **Create** → **Pages** → **Upload assets**.
3. Nombre del proyecto: `donexto` (o similar).
4. Sube **todos** los archivos de esta carpeta:
   - `index.html`
   - `styles.css`
   - `app.js`
   - `favicon.svg`
5. **Deploy site**.
6. Cuando termine: **Custom domains** → **Set up a custom domain** → `donexto.com` y opcional `www.donexto.com`.
7. Cloudflare creará el DNS (CNAME/A) automáticamente. Espera a **Active**.

## Probar en local

Abre `index.html` en el navegador, o:

```bash
cd landing/donexto
# Python
python -m http.server 5500
```

Luego `http://127.0.0.1:5500`

## Lista de espera

El formulario abre un **mailto** a `hello@` / `hola@donexto.com` (ya reenviados a Gmail).  
Más adelante se puede conectar Formspree / Worker sin rehacer el diseño.

## Checklist post-deploy

- [ ] `https://donexto.com` carga
- [ ] Botón ES/EN cambia textos
- [ ] Formulario abre correo de marca
- [ ] Enlaces IG / TikTok / FB / YouTube abren
