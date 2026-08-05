#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT/frontend"
BACKEND_DIR="$ROOT/backend"
FRONTEND_PORT=3000
BACKEND_PORT=8000
RUNTIME_DIR="${TMPDIR:-/tmp}/hms-ai-assistant-${CODESPACE_NAME:-local}"
FRONTEND_LOG="$RUNTIME_DIR/frontend.log"
FRONTEND_PID_FILE="$RUNTIME_DIR/frontend.pid"

mkdir -p "$RUNTIME_DIR"

http_ok() {
  curl -fsS --max-time 5 "$1" >/dev/null 2>&1
}

frontend_processes() {
  local proc pid cwd cmd
  for proc in /proc/[0-9]*; do
    pid="${proc##*/}"
    cwd="$(readlink -f "$proc/cwd" 2>/dev/null || true)"
    [[ "$cwd" == "$FRONTEND_DIR"* ]] || continue
    cmd="$(tr '\0' ' ' < "$proc/cmdline" 2>/dev/null || true)"
    if [[ "$cmd" == *"next dev"* || "$cmd" == *"npm run dev"* ]]; then
      printf '%s\n' "$pid"
    fi
  done
}

stop_frontend() {
  local pids pid

  pids="$(frontend_processes | sort -u || true)"
  if [[ -n "$pids" ]]; then
    while read -r pid; do
      [[ -n "$pid" ]] && kill "$pid" 2>/dev/null || true
    done <<< "$pids"
  fi

  if command -v fuser >/dev/null 2>&1; then
    fuser -k "${FRONTEND_PORT}/tcp" >/dev/null 2>&1 || true
    fuser -k "3100/tcp" >/dev/null 2>&1 || true
  fi

  for _ in $(seq 1 15); do
    if ! http_ok "http://127.0.0.1:${FRONTEND_PORT}/"; then
      break
    fi
    sleep 1
  done

  pids="$(frontend_processes | sort -u || true)"
  if [[ -n "$pids" ]]; then
    while read -r pid; do
      [[ -n "$pid" ]] && kill -9 "$pid" 2>/dev/null || true
    done <<< "$pids"
  fi

  rm -f "$FRONTEND_PID_FILE" "$FRONTEND_DIR/.next/dev/lock"
}

start_frontend() {
  if http_ok "http://127.0.0.1:${FRONTEND_PORT}/"; then
    echo "FRONTEND_${FRONTEND_PORT}=200 (ya activo)"
    return 0
  fi

  : > "$FRONTEND_LOG"

  (
    cd "$FRONTEND_DIR"
    nohup env NEXT_TELEMETRY_DISABLED=1 \
      npm run dev:webpack \
      >>"$FRONTEND_LOG" 2>&1 &
    echo "$!" > "$FRONTEND_PID_FILE"
  )

  local pid
  pid="$(cat "$FRONTEND_PID_FILE")"

  for _ in $(seq 1 60); do
    if http_ok "http://127.0.0.1:${FRONTEND_PORT}/"; then
      echo "FRONTEND_${FRONTEND_PORT}=200"
      show_mode
      return 0
    fi

    if ! kill -0 "$pid" 2>/dev/null; then
      echo "ERROR: el frontend terminó durante el arranque."
      tail -n 60 "$FRONTEND_LOG" 2>/dev/null || true
      return 1
    fi

    sleep 1
  done

  echo "ERROR: el frontend no respondió en 60 segundos."
  tail -n 60 "$FRONTEND_LOG" 2>/dev/null || true
  return 1
}

show_mode() {
  local cmd
  cmd="$(
    for pid in $(frontend_processes | sort -u); do
      tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true
      printf '\n'
    done
  )"

  if [[ "$cmd" == *"--webpack"* ]]; then
    echo "FRONTEND_MODE=WEBPACK"
  elif [[ "$cmd" == *"next dev"* ]]; then
    echo "FRONTEND_MODE=TURBOPACK_O_DESCONOCIDO"
  else
    echo "FRONTEND_MODE=NO_DETECTADO"
  fi
}

status() {
  if http_ok "http://127.0.0.1:${FRONTEND_PORT}/"; then
    echo "FRONTEND_${FRONTEND_PORT}=200"
    show_mode
  else
    echo "FRONTEND_${FRONTEND_PORT}=DOWN"
  fi

  if http_ok "http://127.0.0.1:${BACKEND_PORT}/health"; then
    echo "BACKEND_${BACKEND_PORT}=200"
  else
    echo "BACKEND_${BACKEND_PORT}=DOWN"
  fi
}

repair_frontend() {
  echo "Sustituyendo el proceso anterior por Next.js con Webpack..."
  stop_frontend
  sleep 2
  start_frontend

  echo "Frontend local: http://127.0.0.1:${FRONTEND_PORT}"
  if [[ -n "${CODESPACE_NAME:-}" ]]; then
    echo "HMS Codespaces: https://${CODESPACE_NAME}-${FRONTEND_PORT}.app.github.dev"
  fi
}

logs() {
  tail -n 100 "$FRONTEND_LOG" 2>/dev/null || true
}

case "${1:-status}" in
  start)
    start_frontend
    ;;
  status)
    status
    ;;
  repair)
    case "${2:-frontend}" in
      frontend) repair_frontend ;;
      *) echo "Uso: ./hms repair frontend"; exit 2 ;;
    esac
    ;;
  logs)
    logs
    ;;
  *)
    cat <<'EOF'
Uso:
  ./hms status
  ./hms start
  ./hms repair frontend
  ./hms logs frontend
EOF
    exit 2
    ;;
esac
