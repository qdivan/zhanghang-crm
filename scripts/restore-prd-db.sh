#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA_DIR="$ROOT_DIR/infra"
ENV_DIR="$INFRA_DIR/env"
COMPOSE_FILE="$INFRA_DIR/docker-compose.prd.yml"
POSTGRES_ENV="$ENV_DIR/postgres.prd.env"
API_ENV="$ENV_DIR/api.prd.env"
BACKUP_SCRIPT="$ROOT_DIR/scripts/backup-prd-db.sh"

usage() {
  cat <<'USAGE'
用法:
  bash ./scripts/restore-prd-db.sh --dump <path/to/postgres.dump> --confirm <POSTGRES_DB> [--skip-pre-backup]

说明:
  - 这是生产恢复脚本，会覆盖当前生产数据库
  - 默认会先执行一次恢复前备份
  - 只有 --confirm 与当前 POSTGRES_DB 完全一致时才会继续
USAGE
}

DUMP_FILE=""
CONFIRM_NAME=""
SKIP_PRE_BACKUP=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dump)
      DUMP_FILE="$2"
      shift 2
      ;;
    --confirm)
      CONFIRM_NAME="$2"
      shift 2
      ;;
    --skip-pre-backup)
      SKIP_PRE_BACKUP=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

require_file() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    echo "Missing required file: $path" >&2
    exit 1
  fi
}

if [[ -z "$DUMP_FILE" || -z "$CONFIRM_NAME" ]]; then
  usage >&2
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  echo "docker compose is required" >&2
  exit 1
fi

require_file "$COMPOSE_FILE"
require_file "$POSTGRES_ENV"
require_file "$API_ENV"
require_file "$DUMP_FILE"

ensure_local_image_overrides() {
  if [[ -z "${API_IMAGE:-}" ]] && docker image inspect daizhang-api:prd-local >/dev/null 2>&1; then
    export API_IMAGE="daizhang-api:prd-local"
  fi
  if [[ -z "${WEB_IMAGE:-}" ]] && docker image inspect daizhang-web:prd-local >/dev/null 2>&1; then
    export WEB_IMAGE="daizhang-web:prd-local"
  fi
}

set -a
source "$POSTGRES_ENV"
set +a

: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"

ensure_local_image_overrides

if [[ "$CONFIRM_NAME" != "$POSTGRES_DB" ]]; then
  echo "Refusing to restore. --confirm must exactly match POSTGRES_DB ($POSTGRES_DB)." >&2
  exit 1
fi

restart_app_services() {
  cd "$INFRA_DIR"
  "${COMPOSE[@]}" -f "$COMPOSE_FILE" up -d api web >/dev/null || true
}

wait_for_postgres() {
  "${COMPOSE[@]}" -f "$COMPOSE_FILE" exec -T postgres sh -lc '
    export PGPASSWORD="$POSTGRES_PASSWORD"
    until pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; do
      sleep 1
    done
  '
}

trap restart_app_services EXIT

if [[ "$SKIP_PRE_BACKUP" -ne 1 ]]; then
  bash "$BACKUP_SCRIPT" --label "pre-restore"
fi

cd "$INFRA_DIR"
"${COMPOSE[@]}" -f "$COMPOSE_FILE" up -d postgres >/dev/null
wait_for_postgres
"${COMPOSE[@]}" -f "$COMPOSE_FILE" stop api web >/dev/null || true

"${COMPOSE[@]}" -f "$COMPOSE_FILE" exec -T postgres sh -lc '
  export PGPASSWORD="$POSTGRES_PASSWORD"
  psql -U "$POSTGRES_USER" -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '\''$POSTGRES_DB'\'' AND pid <> pg_backend_pid();" >/dev/null
  dropdb -U "$POSTGRES_USER" --if-exists "$POSTGRES_DB"
  createdb -U "$POSTGRES_USER" "$POSTGRES_DB"
'

cat "$DUMP_FILE" | "${COMPOSE[@]}" -f "$COMPOSE_FILE" exec -T postgres sh -lc '
  export PGPASSWORD="$POSTGRES_PASSWORD"
  pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-privileges
'

"${COMPOSE[@]}" -f "$COMPOSE_FILE" exec -T postgres sh -lc '
  export PGPASSWORD="$POSTGRES_PASSWORD"
  psql -U "$POSTGRES_USER" -d postgres -c "CHECKPOINT" >/dev/null
'

trap - EXIT
restart_app_services

echo "Production restore completed from: $DUMP_FILE"
echo "  Database: $POSTGRES_DB"
