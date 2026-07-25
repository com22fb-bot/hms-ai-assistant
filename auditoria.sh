#!/usr/bin/env bash

set -u

echo "============================================================"
echo " HMS AI ASSISTANT - AUDITORÍA COMPLETA DEL PROYECTO"
echo "============================================================"

echo
echo "==================== GIT ===================="
git status
echo
git branch -a
echo
git log --oneline --decorate --graph -20

echo
echo "==================== ESTRUCTURA ===================="

find backend frontend supabase \
  -type f \
  ! -path "*/node_modules/*" \
  ! -path "*/.next/*" \
  ! -path "*/__pycache__/*" \
  ! -path "*/.git/*" \
  ! -name "*.pyc" \
  ! -name ".env" \
  ! -name ".env.local" \
  ! -name "*.ico" \
  ! -name "*.png" \
  ! -name "*.jpg" \
  ! -name "*.jpeg" \
  ! -name "*.gif" \
  ! -name "*.webp" \
  ! -name "*.pdf" \
  ! -name "*.zip" \
  ! -name "*.woff" \
  ! -name "*.woff2" \
  ! -name "*.ttf" \
  ! -name "*.eot" \
  ! -name "package-lock.json" \
  | sort

print_text_files() {
  section="$1"
  directory="$2"

  echo
  echo "==================== $section ===================="

  while IFS= read -r file
  do
    echo
    echo "############################################################"
    echo "# FILE: $file"
    echo "############################################################"

    if [[ ! -s "$file" ]]; then
      echo "[ARCHIVO VACÍO]"
    elif grep -Iq . "$file"; then
      cat "$file"
    else
      echo "[ARCHIVO BINARIO OMITIDO]"
    fi
  done < <(
    find "$directory" \
      -type f \
      ! -path "*/node_modules/*" \
      ! -path "*/.next/*" \
      ! -path "*/__pycache__/*" \
      ! -path "*/.git/*" \
      ! -name "*.pyc" \
      ! -name ".env" \
      ! -name ".env.local" \
      ! -name "*.ico" \
      ! -name "*.png" \
      ! -name "*.jpg" \
      ! -name "*.jpeg" \
      ! -name "*.gif" \
      ! -name "*.webp" \
      ! -name "*.pdf" \
      ! -name "*.zip" \
      ! -name "*.woff" \
      ! -name "*.woff2" \
      ! -name "*.ttf" \
      ! -name "*.eot" \
      ! -name "package-lock.json" \
      | sort
  )
}

print_text_files "BACKEND" "backend"
print_text_files "FRONTEND" "frontend"
print_text_files "SUPABASE" "supabase"

echo
echo "==================== PACKAGE.JSON RAÍZ ===================="
if [[ -f package.json ]]; then
  cat package.json
else
  echo "[NO EXISTE package.json EN LA RAÍZ]"
fi

echo
echo "==================== FRONTEND PACKAGE.JSON ===================="
if [[ -f frontend/package.json ]]; then
  cat frontend/package.json
else
  echo "[NO EXISTE frontend/package.json]"
fi

echo
echo "==================== REQUIREMENTS ===================="
if [[ -f backend/requirements.txt ]]; then
  cat backend/requirements.txt
else
  echo "[NO EXISTE backend/requirements.txt]"
fi

echo
echo "==================== FIN DE LA AUDITORÍA ===================="