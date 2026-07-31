#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(git rev-parse --show-toplevel)"

printf '\n[%s] Verificando Sprint 4.3\n' "$(date '+%Y-%m-%d %H:%M:%S')"

python -m compileall -q backend/app backend/main.py
echo "Backend Python: OK"

python - <<'PY'
from app.services.case_engine import normalize_subject

assert normalize_subject("RE: FWD: Factura 005") == "factura 005"
assert normalize_subject(" Solicitud   de pago ") == "solicitud de pago"

print("Case Engine unit checks: OK")
PY

(
  cd frontend
  npm run lint
)

echo "Frontend lint: OK"
git diff --check
echo "Git diff: OK"

printf '[%s] Sprint 4.3 verificado\n' "$(date '+%Y-%m-%d %H:%M:%S')"
