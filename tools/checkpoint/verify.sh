#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"
ROOT="$(repo_root)"; cd "$ROOT"
log "Validando repositorio"
git diff --check
if [[ -d backend/app ]]; then require_cmd python; python -m compileall -q backend/app; log "Backend Python: OK"; fi
if [[ -f frontend/package.json ]]; then
 require_cmd npm
 (cd frontend; if npm run | grep -qE ' lint($|:)'; then npm run lint; fi)
 log "Frontend: validación ejecutada"
fi
log "Validaciones completadas"
