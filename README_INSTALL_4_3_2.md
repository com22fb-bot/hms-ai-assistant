# HMS AI Assistant 4.3.2

## Correcciones

- Lotes de 50 mensajes.
- Detección masiva de duplicados.
- Procesamiento de casos separado de la descarga.
- Progreso visible desde el lote 1.
- Encabezado compacto.
- Hero visible en laptop.
- Diseño responsive corregido.
- Se conservan los cuatro temas.

## Instalación

```bash
cd /workspaces/hms-ai-assistant
unzip -o hms-ai-assistant-4.3.2-sync-performance-ui-v2.zip
rm -f hms-ai-assistant-4.3.2-sync-performance-ui-v2.zip

PYTHONPATH=backend python3 -m compileall -q backend/app

cd frontend
npm run lint
npm run build
```
