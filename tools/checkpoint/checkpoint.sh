#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; source "$SCRIPT_DIR/lib.sh"
ROOT="$(repo_root)"; cd "$ROOT"
require_cmd git; ensure_safe_git_state; ensure_origin
git config --local commit.gpgsign false; git config --local tag.gpgsign false
STAMP="$(date +%Y%m%d-%H%M%S)"; TODAY="$(date +%Y-%m-%d)"; RESTORE_DIR="docs/restorepoints/$STAMP"; mkdir -p "$RESTORE_DIR"
log "Creando documentación estratégica"; "$SCRIPT_DIR/create_docs.sh" "$TODAY"
log "Ejecutando validaciones"; "$SCRIPT_DIR/verify.sh" | tee "$RESTORE_DIR/VALIDACIONES.log"
cat > "$RESTORE_DIR/RESTOREPOINT.md" <<EOF
# Restore point — $STAMP

- Fecha: $(date)
- Rama: $(current_branch)
- Remoto: $(git remote get-url origin)

Checkpoint estratégico 2.0 y sistema permanente de respaldo del proyecto.
EOF
git add -A
SENSITIVE="$(sensitive_staged_files)"; if [[ -n "$SENSITIVE" ]]; then git reset; fail "Se detectaron archivos sensibles:\n$SENSITIVE"; fi
if git diff --cached --quiet; then log "No hay cambios nuevos para commit"; else git commit -m "docs: checkpoint estratégico 2.0 y toolkit de respaldos"; fi
log "Creando respaldo completo"; "$SCRIPT_DIR/backup.sh" "$STAMP" | tee "$RESTORE_DIR/BACKUP.log"
log "Checkpoint completado"; git log -1 --oneline; git status --short
printf '\nPara detener Codespaces cuando termines:\ngh codespace stop\n'
