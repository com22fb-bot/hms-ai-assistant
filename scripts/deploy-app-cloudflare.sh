#!/usr/bin/env bash
# Deploy Donexto app (Next.js → Cloudflare Workers) from repo root or frontend/
# Usage (Codespace):
#   export NEXT_PUBLIC_SUPABASE_URL=...
#   export NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=...
#   ./scripts/deploy-app-cloudflare.sh

set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT/frontend"

if [[ -z "${NEXT_PUBLIC_SUPABASE_URL:-}" || -z "${NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY:-}" ]]; then
  echo "ERROR: exporta NEXT_PUBLIC_SUPABASE_URL y NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY antes de desplegar."
  exit 1
fi

export HMS_INTERNAL_API_BASE_URL="${HMS_INTERNAL_API_BASE_URL:-https://hms-ai-assistant-production.up.railway.app}"
# Same-origin proxy; do not force public API unless needed
unset NEXT_PUBLIC_API_BASE_URL || true

cd "$FRONTEND_DIR"

if [[ ! -d node_modules ]]; then
  npm ci
fi

echo "Building + deploying Donexto app (Cloudflare)..."
echo "  HMS_INTERNAL_API_BASE_URL=$HMS_INTERNAL_API_BASE_URL"
npm run deploy

echo ""
echo "Listo. En Cloudflare Workers & Pages → donexto-app → Domains → app.donexto.com"
echo "En Railway Variables: FRONTEND_ORIGINS=https://app.donexto.com"
echo "En Supabase Auth → URL config: Site URL + Redirect URLs para https://app.donexto.com"
