#!/usr/bin/env bash
set -Eeuo pipefail
log(){ printf '\n[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
fail(){ printf '\nERROR: %s\n' "$*" >&2; exit 1; }
require_cmd(){ command -v "$1" >/dev/null 2>&1 || fail "Falta el comando requerido: $1"; }
repo_root(){ git rev-parse --show-toplevel 2>/dev/null || fail "No estás dentro de un repositorio Git."; }
current_branch(){ git branch --show-current; }
ensure_safe_git_state(){
 [[ ! -d .git/rebase-merge ]] || fail "Hay un rebase pendiente."
 [[ ! -d .git/rebase-apply ]] || fail "Hay un rebase pendiente."
 [[ ! -f .git/MERGE_HEAD ]] || fail "Hay un merge pendiente."
 [[ ! -f .git/CHERRY_PICK_HEAD ]] || fail "Hay un cherry-pick pendiente."
}
ensure_origin(){ git remote get-url origin >/dev/null 2>&1 || fail "No existe el remoto origin."; }
sensitive_staged_files(){ git diff --cached --name-only | grep -Ei '(^|/)(\.env|\.env\.[^/]+|.*\.pem|.*\.p12|.*\.pfx|.*\.key|credentials\.json|service[_-]?account.*\.json)$' | grep -Evi '(\.example|\.sample|\.template)$' || true; }
