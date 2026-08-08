#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

ROOT="$(repo_root)"
cd "$ROOT"

log "Validando repositorio"
git diff --check

if [[ -d backend/app ]]; then
  require_cmd python
  python -m compileall -q backend/app
  log "Backend Python: OK"
fi

if [[ -f frontend/package.json ]]; then
  require_cmd npm
  require_cmd node

  if (
    cd frontend
    node -e 'const p=require("./package.json"); process.exit(p.scripts?.lint ? 0 : 1);'
  ); then
    (cd frontend && npm run lint)
    log "Frontend lint: OK"
  else
    log "Frontend: no existe script lint; se omite"
  fi
fi

log "Validaciones completadas"
