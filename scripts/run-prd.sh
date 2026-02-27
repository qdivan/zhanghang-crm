#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA_DIR="$ROOT_DIR/infra"
ENV_DIR="$INFRA_DIR/env"

ensure_env_file() {
  local target_file="$1"
  local example_file="$2"
  if [[ ! -f "$target_file" ]]; then
    cp "$example_file" "$target_file"
    echo "Created $target_file from example. Please update secrets before real production use."
  fi
}

ensure_env_file "$ENV_DIR/api.prd.env" "$ENV_DIR/api.prd.env.example"
ensure_env_file "$ENV_DIR/postgres.prd.env" "$ENV_DIR/postgres.prd.env.example"

docker build \
  -t daizhang-api:prd-local \
  -f "$ROOT_DIR/apps/api/Dockerfile.prod" \
  "$ROOT_DIR/apps/api"

docker build \
  -t daizhang-web:prd-local \
  -f "$ROOT_DIR/apps/web/Dockerfile.prod" \
  "$ROOT_DIR/apps/web"

cd "$INFRA_DIR"
API_IMAGE=daizhang-api:prd-local \
WEB_IMAGE=daizhang-web:prd-local \
docker compose -f docker-compose.prd.yml up -d --remove-orphans

echo "PRD stack is up:"
echo "  Web: http://127.0.0.1:31080"
echo "  API: http://127.0.0.1:31000/api/v1/health"
