#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA_DIR="$ROOT_DIR/infra"
ENV_DIR="$INFRA_DIR/env"
COMPOSE_FILE="$INFRA_DIR/docker-compose.prd.yml"
POSTGRES_ENV="$ENV_DIR/postgres.prd.env"
API_ENV="$ENV_DIR/api.prd.env"
BACKUP_ROOT="$ROOT_DIR/backups/prd"

usage() {
  cat <<'USAGE'
用法:
  bash ./scripts/backup-prd-db.sh [--output-dir <dir>] [--label <name>]

说明:
  - 读取 infra/env/postgres.prd.env 中的生产库配置
  - 使用生产 docker compose 栈里的 postgres 容器执行 pg_dump
  - 输出到 backups/prd/<timestamp>[-label]/
USAGE
}

OUTPUT_DIR=""
LABEL=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --label)
      LABEL="$2"
      shift 2
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

set -a
source "$POSTGRES_ENV"
set +a

: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"

wait_for_postgres() {
  "${COMPOSE[@]}" -f "$COMPOSE_FILE" exec -T postgres sh -lc '
    export PGPASSWORD="$POSTGRES_PASSWORD"
    until pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; do
      sleep 1
    done
  '
}

TIMESTAMP="$(date '+%Y%m%d-%H%M%S')"
if [[ -z "$OUTPUT_DIR" ]]; then
  OUTPUT_DIR="$BACKUP_ROOT/$TIMESTAMP"
  if [[ -n "$LABEL" ]]; then
    OUTPUT_DIR+="-$LABEL"
  fi
fi

umask 077
mkdir -p "$OUTPUT_DIR"

DUMP_FILE="$OUTPUT_DIR/postgres.dump"
CONFIG_ARCHIVE="$OUTPUT_DIR/config.tar.gz"
MANIFEST_FILE="$OUTPUT_DIR/manifest.txt"

cd "$INFRA_DIR"
"${COMPOSE[@]}" -f "$COMPOSE_FILE" up -d postgres >/dev/null
wait_for_postgres

"${COMPOSE[@]}" -f "$COMPOSE_FILE" exec -T postgres sh -lc '
  export PGPASSWORD="$POSTGRES_PASSWORD"
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc
' > "$DUMP_FILE"

EXISTING_CONFIG_FILES=()
for relative_path in \
  "infra/docker-compose.prd.yml" \
  "infra/env/api.prd.env" \
  "infra/env/postgres.prd.env"; do
  if [[ -f "$ROOT_DIR/$relative_path" ]]; then
    EXISTING_CONFIG_FILES+=("$relative_path")
  fi
done

tar -czf "$CONFIG_ARCHIVE" -C "$ROOT_DIR" "${EXISTING_CONFIG_FILES[@]}"

{
  echo "backup_created_at=$(date '+%Y-%m-%d %H:%M:%S %z')"
  echo "backup_output_dir=$OUTPUT_DIR"
  echo "database_name=$POSTGRES_DB"
  echo "database_user=$POSTGRES_USER"
  echo "compose_file=$COMPOSE_FILE"
  echo "api_env=$API_ENV"
  echo "postgres_env=$POSTGRES_ENV"
  if git -C "$ROOT_DIR" rev-parse HEAD >/dev/null 2>&1; then
    echo "git_revision=$(git -C "$ROOT_DIR" rev-parse HEAD)"
  fi
} > "$MANIFEST_FILE"

ln -sfn "$OUTPUT_DIR" "$BACKUP_ROOT/latest"

echo "Production backup completed: $OUTPUT_DIR"
echo "  Dump: $DUMP_FILE"
echo "  Config: $CONFIG_ARCHIVE"
echo "  Manifest: $MANIFEST_FILE"
