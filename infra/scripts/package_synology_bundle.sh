#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUTPUT_PATH="${1:-$ROOT_DIR/output/release/daizhang-synology-src.tar.gz}"

mkdir -p "$(dirname "$OUTPUT_PATH")"
export COPYFILE_DISABLE=1
export COPY_EXTENDED_ATTRIBUTES_DISABLE=1

tar \
  --exclude=".git" \
  --exclude=".playwright-cli" \
  --exclude=".codex" \
  --exclude="node_modules" \
  --exclude="apps/web/node_modules" \
  --exclude="apps/web/dist" \
  --exclude="apps/api/.venv" \
  --exclude="apps/api/*.db" \
  --exclude="apps/api/*.sqlite" \
  --exclude="apps/api/*.sqlite3" \
  --exclude="output/playwright" \
  --exclude="output/release" \
  --exclude="*.xls" \
  --exclude="*.xlsx" \
  -czf "$OUTPUT_PATH" \
  -C "$ROOT_DIR" .

echo "Bundle created at: $OUTPUT_PATH"
