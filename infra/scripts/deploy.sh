#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <dev|prd> [api_image] [web_image]"
  exit 1
fi

TARGET_ENV="$1"
API_IMAGE_OVERRIDE="${2:-}"
WEB_IMAGE_OVERRIDE="${3:-}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

case "$TARGET_ENV" in
  dev)
    COMPOSE_FILE="$ROOT_DIR/docker-compose.dev.yml"
    ;;
  prd)
    COMPOSE_FILE="$ROOT_DIR/docker-compose.prd.yml"
    ;;
  *)
    echo "Unknown environment: $TARGET_ENV"
    exit 1
    ;;
esac

if [[ -n "$API_IMAGE_OVERRIDE" ]]; then
  export API_IMAGE="$API_IMAGE_OVERRIDE"
fi

if [[ -n "$WEB_IMAGE_OVERRIDE" ]]; then
  export WEB_IMAGE="$WEB_IMAGE_OVERRIDE"
fi

echo "Deploying $TARGET_ENV with compose file: $COMPOSE_FILE"
docker compose -f "$COMPOSE_FILE" pull
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

echo "Deployment finished for $TARGET_ENV"
