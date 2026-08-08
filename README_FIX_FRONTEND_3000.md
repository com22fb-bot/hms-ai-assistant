# HMS — frontend oficial en el puerto 3000

Este parche corrige la administración local de servicios. No toca Gmail,
Supabase, OAuth, mensajes ni casos.

## Configuración definitiva

- Frontend Next.js: `3000`
- Backend FastAPI: `8000`
- Puerto temporal `3100`: retirado

## Instalación

```bash
cd /workspaces/hms-ai-assistant
tar -xzf HMS_FRONTEND_3000_RAIZ_5.tar.gz
chmod +x hms scripts/hms-dev.sh
./hms repair
```

## Uso posterior

```bash
./hms start
./hms status
./hms repair
./hms logs frontend
./hms logs backend
```

## Reinicio del túnel 3000 de Codespaces

El controlador verifica que Next.js responda internamente. El túnel público es
administrado por GitHub Codespaces y no puede reconstruirse desde Next.js.

Después de que `./hms repair` muestre `FRONTEND_3000=200`:

1. Abre la pestaña **PUERTOS**.
2. En el puerto 3000 anterior, usa **Detener reenvío del puerto**.
3. Pulsa **Agregar puerto** y escribe `3000`.
4. Abre el nuevo enlace del puerto 3000.
5. Mantén el protocolo en HTTP. La URL externa seguirá usando HTTPS.

Esto elimina el túnel obsoleto que anteriormente devolvía 404.
