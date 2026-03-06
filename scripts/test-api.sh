#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"

cd "$API_DIR"

if [[ -x ".venv/bin/python" ]]; then
  .venv/bin/python -m pytest "$@"
else
  python3 -m pytest "$@"
fi
