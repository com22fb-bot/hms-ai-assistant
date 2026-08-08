# Instalación del Sprint 4.3

## 1. Subir y descomprimir

Coloca este ZIP en `/workspaces/hms-ai-assistant` y ejecuta:

```bash
cd /workspaces/hms-ai-assistant
unzip -o hms-ai-assistant-sprint-4.3-intelligent-case-engine.zip
chmod +x tools/sprint43/verify.sh
git status --short
```

## 2. Aplicar la migración de Supabase

Primero intenta:

```bash
supabase db push
```

Si el comando `supabase` no existe:

```bash
npx supabase db push
```

## 3. Verificar código

```bash
cd /workspaces/hms-ai-assistant
PYTHONPATH=backend ./tools/sprint43/verify.sh
```

## 4. Commit

Solo cuando la migración y las validaciones terminen correctamente:

```bash
git add -A
git commit -m "feat(sprint-4.3): implement intelligent case engine"
git push origin sprint-4.1-ui
```

## 5. Probar API

Con el backend ejecutándose:

```bash
curl -X POST "http://127.0.0.1:8000/cases/process?limit=500"
curl "http://127.0.0.1:8000/cases/dashboard"
curl "http://127.0.0.1:8000/cases"
```

## 6. Checkpoint

Después de validar la interfaz y la API:

```bash
./tools/checkpoint/checkpoint.sh "4.3"
```
