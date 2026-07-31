#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

ROOT="$(repo_root)"
cd "$ROOT"

require_cmd git
require_cmd python
ensure_safe_git_state
ensure_origin

git config --local commit.gpgsign false
git config --local tag.gpgsign false

SPRINT="${1:-${SPRINT:-SIN_ASIGNAR}}"
STAMP="$(date +%Y%m%d-%H%M%S)"
CHECKPOINT_ID="HMS-CP-$STAMP"
CHECKPOINT_DATE="$(date +%Y-%m-%d)"
CHECKPOINT_TIME="$(date +%H:%M:%S)"
CHECKPOINT_TZ="$(date +%Z)"
BRANCH="$(current_branch)"
[[ -n "$BRANCH" ]] || fail "No se pudo determinar la rama actual."

RESTORE_DIR="docs/restorepoints/$CHECKPOINT_ID"
VALIDATION_LOG="$RESTORE_DIR/VALIDACIONES.log"
RESTORE_FILE="$RESTORE_DIR/RESTOREPOINT.md"
MANIFEST_FILE="$RESTORE_DIR/CHECKPOINT.env"
BACKUP_BRANCH="backup/$CHECKPOINT_ID"
BACKUP_TAG="restorepoint-$CHECKPOINT_ID"
BACKUP_DIR="${BACKUP_DIR:-/workspaces/backups}"
BUNDLE_FILE="$BACKUP_DIR/hms-ai-assistant-$CHECKPOINT_ID.bundle"

mkdir -p "$RESTORE_DIR" "$BACKUP_DIR"

log "Checkpoint $CHECKPOINT_ID — inicio"
log "Sprint: $SPRINT | Rama: $BRANCH"
log "Ejecutando validaciones"
"$SCRIPT_DIR/verify.sh" | tee "$VALIDATION_LOG"

cat > "$RESTORE_FILE" <<EOF
# Restore Point — $CHECKPOINT_ID

## Identificación

- **Checkpoint ID:** $CHECKPOINT_ID
- **Proyecto:** HMS AI Assistant
- **Fecha:** $CHECKPOINT_DATE
- **Hora:** $CHECKPOINT_TIME
- **Zona horaria del entorno:** $CHECKPOINT_TZ
- **Sprint:** $SPRINT
- **Rama de origen:** $BRANCH
- **Estado:** REGISTRADO

## Trazabilidad Git

- **Commit de snapshot:** PENDING_SNAPSHOT_COMMIT
- **Commit de registro:** es el commit apuntado por el tag \`$BACKUP_TAG\`
- **Tag:** \`$BACKUP_TAG\`
- **Rama de respaldo:** \`$BACKUP_BRANCH\`
- **Bundle:** \`$BUNDLE_FILE\`
- **Remoto:** \`$(git remote get-url origin)\`

## Convención

El commit de snapshot conserva el contenido funcional y documental existente al iniciar el checkpoint.
El commit de registro agrega esta trazabilidad. El tag y la rama de respaldo apuntan al commit de registro.

## Verificación

\`git rev-list -n 1 $BACKUP_TAG\`

\`git show --stat $BACKUP_TAG\`
EOF

cat > "$MANIFEST_FILE" <<EOF
CHECKPOINT_ID=$CHECKPOINT_ID
CHECKPOINT_DATE=$CHECKPOINT_DATE
CHECKPOINT_TIME=$CHECKPOINT_TIME
CHECKPOINT_TIMEZONE=$CHECKPOINT_TZ
SPRINT=$SPRINT
SOURCE_BRANCH=$BRANCH
SNAPSHOT_COMMIT=PENDING_SNAPSHOT_COMMIT
BACKUP_BRANCH=$BACKUP_BRANCH
BACKUP_TAG=$BACKUP_TAG
BUNDLE_FILE=$BUNDLE_FILE
EOF

git add -A
SENSITIVE="$(sensitive_staged_files)"
if [[ -n "$SENSITIVE" ]]; then
  git reset
  fail "Se detectaron archivos sensibles:\n$SENSITIVE"
fi

git commit -m "checkpoint($CHECKPOINT_ID): snapshot Sprint $SPRINT"
SNAPSHOT_COMMIT="$(git rev-parse HEAD)"

python - "$RESTORE_FILE" "$MANIFEST_FILE" "$SNAPSHOT_COMMIT" <<'PY'
from pathlib import Path
import sys

for filename in sys.argv[1:3]:
    path = Path(filename)
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace("PENDING_SNAPSHOT_COMMIT", sys.argv[3]),
        encoding="utf-8",
    )
PY

git add "$RESTORE_FILE" "$MANIFEST_FILE"
git commit -m "docs(checkpoint): register $CHECKPOINT_ID"
CHECKPOINT_COMMIT="$(git rev-parse HEAD)"

log "Creando respaldo completo"
"$SCRIPT_DIR/backup.sh" "$CHECKPOINT_ID" "$CHECKPOINT_COMMIT" \
  | tee "$BACKUP_DIR/hms-ai-assistant-$CHECKPOINT_ID.log"

log "Checkpoint $CHECKPOINT_ID completado"
printf '\nCHECKPOINT_ID=%s\nSPRINT=%s\nSNAPSHOT_COMMIT=%s\nCHECKPOINT_COMMIT=%s\nBACKUP_BRANCH=%s\nBACKUP_TAG=%s\nBUNDLE_FILE=%s\n' \
  "$CHECKPOINT_ID" "$SPRINT" "$SNAPSHOT_COMMIT" "$CHECKPOINT_COMMIT" \
  "$BACKUP_BRANCH" "$BACKUP_TAG" "$BUNDLE_FILE"

git log -2 --oneline
git status --short
printf '\nPara detener Codespaces cuando termines:\nstopcs\n'
