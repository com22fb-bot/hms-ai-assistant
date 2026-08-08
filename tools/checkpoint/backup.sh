#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

ROOT="$(repo_root)"
cd "$ROOT"

CHECKPOINT_ID="${1:-HMS-CP-$(date +%Y%m%d-%H%M%S)}"
COMMIT="${2:-$(git rev-parse HEAD)}"
SOURCE_BRANCH="$(current_branch)"
[[ -n "$SOURCE_BRANCH" ]] || fail "No se pudo determinar la rama actual."

BACKUP_BRANCH="backup/$CHECKPOINT_ID"
BACKUP_TAG="restorepoint-$CHECKPOINT_ID"
BACKUP_DIR="${BACKUP_DIR:-/workspaces/backups}"
BUNDLE_FILE="$BACKUP_DIR/hms-ai-assistant-$CHECKPOINT_ID.bundle"

mkdir -p "$BACKUP_DIR"

git rev-parse --verify "$COMMIT^{commit}" >/dev/null \
  || fail "El commit $COMMIT no existe."

if git show-ref --verify --quiet "refs/heads/$BACKUP_BRANCH"; then
  fail "La rama $BACKUP_BRANCH ya existe."
fi

if git show-ref --verify --quiet "refs/tags/$BACKUP_TAG"; then
  fail "El tag $BACKUP_TAG ya existe."
fi

git branch "$BACKUP_BRANCH" "$COMMIT"
git tag -a "$BACKUP_TAG" "$COMMIT" \
  -m "Checkpoint HMS AI Assistant $CHECKPOINT_ID"

git bundle create "$BUNDLE_FILE" --all
git bundle verify "$BUNDLE_FILE"

if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "$BUNDLE_FILE" > "$BUNDLE_FILE.sha256"
fi

git push origin "$SOURCE_BRANCH"
git push origin "$BACKUP_BRANCH"
git push origin "$BACKUP_TAG"

printf '\nCHECKPOINT_ID=%s\nCHECKPOINT_COMMIT=%s\nBACKUP_BRANCH=%s\nBACKUP_TAG=%s\nBUNDLE_FILE=%s\n' \
  "$CHECKPOINT_ID" "$COMMIT" "$BACKUP_BRANCH" "$BACKUP_TAG" "$BUNDLE_FILE"
