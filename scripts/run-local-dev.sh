#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

ensure_port_free() {
  local port="$1"
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Port $port is already in use. Stop existing services first."
    lsof -nP -iTCP:"$port" -sTCP:LISTEN || true
    exit 1
  fi
}

cleanup() {
  if [[ -n "${WEB_PID:-}" ]]; then
    kill "$WEB_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "${API_PID:-}" ]]; then
    kill "$API_PID" >/dev/null 2>&1 || true
  fi
  wait >/dev/null 2>&1 || true
}

trap cleanup INT TERM EXIT

ensure_port_free 8000
ensure_port_free 5173

bash "$ROOT_DIR/scripts/run-local-api.sh" &
API_PID=$!

(
  cd "$ROOT_DIR"
  npm --workspace apps/web run dev -- --host 0.0.0.0 --port 5173
) &
WEB_PID=$!

echo "Local dev is running:"
echo "  Web: http://127.0.0.1:5173"
echo "  API: http://127.0.0.1:8000"
echo "Press Ctrl+C to stop both."

while true; do
  if ! kill -0 "$API_PID" >/dev/null 2>&1; then
    exit 1
  fi
  if ! kill -0 "$WEB_PID" >/dev/null 2>&1; then
    exit 1
  fi
  sleep 1
done
