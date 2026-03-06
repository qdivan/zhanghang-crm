#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"

# Local development defaults:
# - bootstrap demo users/data so fresh sqlite can login immediately
# - keep existing local data by default (no reset)
export BOOTSTRAP_DEMO_DATA="${BOOTSTRAP_DEMO_DATA:-true}"
export BOOTSTRAP_DEMO_PASSWORD="${BOOTSTRAP_DEMO_PASSWORD:-Daizhang#2026!}"
export RESET_DB_ON_STARTUP="${RESET_DB_ON_STARTUP:-false}"

find_uvicorn() {
  if [[ -x "$API_DIR/.venv/bin/uvicorn" ]]; then
    echo "$API_DIR/.venv/bin/uvicorn"
    return 0
  fi

  if command -v uvicorn >/dev/null 2>&1; then
    command -v uvicorn
    return 0
  fi

  return 1
}

UVICORN_BIN="$(find_uvicorn || true)"
if [[ -z "$UVICORN_BIN" ]]; then
  echo "Cannot find uvicorn."
  echo "Setup backend first:"
  echo "  cd apps/api"
  echo "  python3 -m venv .venv"
  echo "  source .venv/bin/activate"
  echo "  pip install -r requirements.txt"
  exit 1
fi

if lsof -nP -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port 8000 is already in use. Stop the running service first."
  lsof -nP -iTCP:8000 -sTCP:LISTEN || true
  exit 1
fi

cd "$API_DIR"
"$UVICORN_BIN" app.main:app --reload --host 0.0.0.0 --port 8000
