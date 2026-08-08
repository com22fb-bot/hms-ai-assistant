#!/usr/bin/env bash
set -Eeuo pipefail

cd /workspaces/hms-ai-assistant

echo "=== PYTHON COMPILE ==="
python3 -m compileall -q backend/app

echo "=== OPENAPI ROUTES ==="
PYTHONPATH=backend python3 - <<'PY'
from main import app

paths = set(app.openapi()["paths"])
required = {
    "/gmail/sync-jobs",
    "/gmail/sync-jobs/active",
    "/gmail/sync-jobs/{job_id}",
    "/gmail/sync-jobs/{job_id}/pause",
    "/gmail/sync-jobs/{job_id}/resume",
    "/gmail/sync-jobs/{job_id}/cancel",
}
missing = sorted(required - paths)
if missing:
    raise SystemExit(f"Faltan rutas: {missing}")
print("RUTAS_DURABLES_OK=1")
PY

echo "=== SUPABASE TABLES ==="
cd /workspaces/hms-ai-assistant/backend
python3 - <<'PY'
from app.services.oauth_storage import OAuthStorage

client = OAuthStorage().client
for table in ("gmail_sync_jobs", "system_incidents"):
    response = client.table(table).select("id", count="exact").limit(1).execute()
    print(f"{table.upper()}_OK=1 COUNT={int(response.count or 0)}")
PY

echo "=== FRONTEND LINT ==="
cd /workspaces/hms-ai-assistant/frontend
npm run lint

echo "=== FRONTEND BUILD ==="
npm run build

echo "SPRINT_4_7_VALIDADO=1"
