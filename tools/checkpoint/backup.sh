#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; source "$SCRIPT_DIR/lib.sh"
ROOT="$(repo_root)"; cd "$ROOT"
STAMP="${1:-$(date +%Y%m%d-%H%M%S)}"; BRANCH="$(current_branch)"; [[ -n "$BRANCH" ]] || fail "No se pudo determinar la rama actual."
BACKUP_BRANCH="backup/hms-checkpoint-$STAMP"; BACKUP_TAG="restorepoint-hms-checkpoint-$STAMP"; BACKUP_DIR="${BACKUP_DIR:-/workspaces/backups}"; BUNDLE_FILE="$BACKUP_DIR/hms-ai-assistant-$STAMP.bundle"
mkdir -p "$BACKUP_DIR"; COMMIT="$(git rev-parse HEAD)"
git branch "$BACKUP_BRANCH" "$COMMIT"
git tag -a "$BACKUP_TAG" "$COMMIT" -m "Checkpoint HMS AI Assistant $STAMP"
git bundle create "$BUNDLE_FILE" --all
git bundle verify "$BUNDLE_FILE"
if command -v sha256sum >/dev/null 2>&1; then sha256sum "$BUNDLE_FILE" > "$BUNDLE_FILE.sha256"; fi
git push origin "$BRANCH"; git push origin "$BACKUP_BRANCH"; git push origin "$BACKUP_TAG"
printf '\nBACKUP_BRANCH=%s\nBACKUP_TAG=%s\nBUNDLE_FILE=%s\n' "$BACKUP_BRANCH" "$BACKUP_TAG" "$BUNDLE_FILE"
