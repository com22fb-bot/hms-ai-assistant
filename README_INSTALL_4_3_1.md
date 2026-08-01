# HMS AI Assistant 4.3.1

## Incluye

- Sincronización histórica completa de Gmail.
- Paginación de 500 mensajes sin límite total.
- Procesamiento automático en Casos Inteligentes.
- Proxy interno entre Next.js y FastAPI.
- Cuatro temas premium.
- Interfaz responsive.
- Progreso visible.

## Instalación

```bash
cd /workspaces/hms-ai-assistant
unzip -o hms-ai-assistant-4.3.1-full-sync-premium-ui.zip
rm -f hms-ai-assistant-4.3.1-full-sync-premium-ui.zip

cat > frontend/.env.local <<'EOF'
NEXT_PUBLIC_API_BASE_URL=/api/hms
HMS_INTERNAL_API_BASE_URL=http://127.0.0.1:8000
EOF

PYTHONPATH=backend python3 -m compileall -q backend/app

cd frontend
npm run lint
npm run build
```

Reiniciar frontend:

```bash
pkill -f "next dev" 2>/dev/null || true
cd /workspaces/hms-ai-assistant/frontend
npm run dev -- --hostname 0.0.0.0 --port 3000
```

Puertos 3000 y 8000 pueden permanecer privados.
