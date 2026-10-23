#!/usr/bin/env bash
# Registra o actualiza un PEDIDO de Héctor en la Bitácora de /admin (public.admin_events).
# Uso:
#   scripts/bitacora_pedido.sh <clave> <pendiente|en_curso|hecho> "<título>" ["<detalle>"] ["<fecha ISO del pedido>"]
# Ejemplo:
#   doppler run -p donexto -c prd -- scripts/bitacora_pedido.sh vault-logins en_curso "Vault: guardar logins" "Yahoo, Microsoft, Google"
# Es idempotente: la misma <clave> actualiza la entrada existente (external_id = pedido-<clave>).
# Requiere SUPABASE_URL y SUPABASE_SECRET_KEY (nunca se imprimen). No incluyas correos, IDs ni secretos.
set -uo pipefail
key="${1:-}"; estado="${2:-pendiente}"; title="${3:-}"; detail="${4:-}"; fecha="${5:-}"
case "$estado" in pendiente|en_curso|hecho) ;; *) echo "estado inválido: $estado" >&2; exit 2;; esac
if [[ -z "$key" || -z "${SUPABASE_URL:-}" || -z "${SUPABASE_SECRET_KEY:-}" ]]; then
  echo "bitácora: faltan clave, SUPABASE_URL o SUPABASE_SECRET_KEY." >&2; exit 2
fi
base="${SUPABASE_URL%/}/rest/v1/admin_events"
auth=(-H "apikey: ${SUPABASE_SECRET_KEY}" -H "Authorization: Bearer ${SUPABASE_SECRET_KEY}" -H "Content-Type: application/json")
existing=$(curl -sS -m 20 "${base}?select=id,meta&external_id=eq.pedido-${key}" "${auth[@]}")
body=$(EXISTING="$existing" python3 - "$key" "$estado" "$title" "$detail" "$fecha" <<'PY'
import json, os, sys, datetime
key, estado, title, detail, fecha = sys.argv[1:6]
rows = json.loads(os.environ.get("EXISTING") or "[]")
meta = (rows[0].get("meta") or {}) if rows else {}
now = datetime.datetime.now(datetime.timezone.utc).isoformat()
hist = meta.get("historial") or []
if not hist or hist[-1].get("estado") != estado:
    hist.append({"estado": estado, "at": now})
meta.update({"kind": "pedido", "estado": estado, "historial": hist})
b = {"meta": meta, "status": "resuelto" if estado == "hecho" else "abierto",
     "ended_at": now if estado == "hecho" else None}
if title: b["title"] = title[:200]
if detail: b["detail"] = detail
if not rows:
    if not title: sys.exit("falta título para un pedido nuevo")
    b.update({"source": "manual", "severity": "info", "created_by": "pedido",
              "external_id": f"pedido-{key}", "detail": detail})
    if fecha: b["occurred_at"] = fecha
elif fecha:
    b["occurred_at"] = fecha
print(json.dumps({"new": not rows, "id": rows[0]["id"] if rows else None, "body": b}))
PY
) || exit 1
new=$(python3 -c 'import json,sys;print(json.loads(sys.argv[1])["new"])' "$body")
payload=$(python3 -c 'import json,sys;print(json.dumps(json.loads(sys.argv[1])["body"]))' "$body")
if [[ "$new" == "True" ]]; then
  out=$(curl -sS -m 20 -X POST "$base?select=id" "${auth[@]}" -H "Prefer: return=representation" -d "$payload")
else
  out=$(curl -sS -m 20 -X PATCH "$base?external_id=eq.pedido-${key}&select=id" "${auth[@]}" -H "Prefer: return=representation" -d "$payload")
fi
id=$(python3 -c 'import json,sys
try: print(json.loads(sys.argv[1])[0]["id"])
except Exception: print("")' "$out")
if [[ -n "$id" ]]; then echo "pedido-${key}: ${estado} (id ${id})"; else echo "bitácora: no se registró pedido-${key}" >&2; exit 1; fi
