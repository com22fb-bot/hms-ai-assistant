#!/usr/bin/env bash
set -Eeuo pipefail

cd /workspaces/hms-ai-assistant || exit 1

echo
echo "============================================================"
echo "PASO 1 — PREPARAR PUNTO DE RESTAURACIÓN"
echo "============================================================"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "ERROR: Esta carpeta no es un repositorio Git."
    exit 1
fi

CURRENT_BRANCH="$(git branch --show-current)"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_BRANCH="backup/hms-communications-vision-${STAMP}"
BACKUP_TAG="restorepoint-hms-communications-${STAMP}"
DOC_DIR="docs/restorepoints/${STAMP}"
BACKUP_DIR="/workspaces/backups"
BUNDLE_FILE="${BACKUP_DIR}/hms-ai-assistant-${STAMP}.bundle"
CHECKSUM_FILE="${BUNDLE_FILE}.sha256"

mkdir -p "${DOC_DIR}" "${BACKUP_DIR}"

cat > .restorepoint_context <<CONTEXT
STAMP='${STAMP}'
CURRENT_BRANCH='${CURRENT_BRANCH}'
BACKUP_BRANCH='${BACKUP_BRANCH}'
BACKUP_TAG='${BACKUP_TAG}'
DOC_DIR='${DOC_DIR}'
BACKUP_DIR='${BACKUP_DIR}'
BUNDLE_FILE='${BUNDLE_FILE}'
CHECKSUM_FILE='${CHECKSUM_FILE}'
CONTEXT

echo
echo "Rama actual:       ${CURRENT_BRANCH}"
echo "Rama de respaldo:  ${BACKUP_BRANCH}"
echo "Etiqueta:          ${BACKUP_TAG}"
echo "Documentación:     ${DOC_DIR}"
echo "Bundle:            ${BUNDLE_FILE}"

echo
echo "Estado actual:"
git status --short

echo
echo "============================================================"
echo "PASO 1 COMPLETADO CORRECTAMENTE"
echo "============================================================"
