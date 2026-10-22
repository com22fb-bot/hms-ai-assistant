#!/usr/bin/env bash
# Agrega un evento a la bitácora de /admin (tabla public.admin_events).
# Uso: scripts/log_admin_event.sh <source> <severity> "<título>" ["<detalle>"] [abierto|resuelto]
#   source:   railway | cloudflare | supabase | github | backup | monitor | deploy | manual
#   severity: info | aviso | grave | critico
# Requiere SUPABASE_URL y SUPABASE_SECRET_KEY en el entorno (nunca se imprimen).
# Nunca hace fallar al llamador: si no puede registrar, avisa y sale con 0.
set -uo pipefail
src="${1:-manual}"; sev="${2:-info}"; title="${3:-}"; detail="${4:-}"; status="${5:-abierto}"
if [[ -z "$title" || -z "${SUPABASE_URL:-}" || -z "${SUPABASE_SECRET_KEY:-}" ]]; then
  echo "bitácora: faltan título, SUPABASE_URL o SUPABASE_SECRET_KEY; no se registró." >&2
  exit 0
fi
body=$(python3 -c 'import json,sys; print(json.dumps({"source":sys.argv[1],"severity":sys.argv[2],"title":sys.argv[3][:200],"detail":sys.argv[4],"status":sys.argv[5],"created_by":sys.argv[6]}))' \
  "$src" "$sev" "$title" "$detail" "$status" "${GITHUB_WORKFLOW:-script}")
code=$(curl -sS -m 20 -o /dev/null -w '%{http_code}' -X POST "${SUPABASE_URL%/}/rest/v1/admin_events" \
  -H "apikey: ${SUPABASE_SECRET_KEY}" -H "Authorization: Bearer ${SUPABASE_SECRET_KEY}" \
  -H "Content-Type: application/json" -H "Prefer: return=minimal" -d "$body" || echo 000)
if [[ "$code" == 2* ]]; then echo "bitácora: evento registrado ($src/$sev)."; else echo "bitácora: no se registró (HTTP $code)." >&2; fi
exit 0
