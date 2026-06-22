#!/usr/bin/env bash
# 备份 PostgreSQL（pg_dump）+ 配置，存到 backups/。升级前自动调用。
# 用法：./backup.sh
set -euo pipefail
COMPOSE="compose/docker-compose.prod.yml"
ENVFILE="config/.env"
TS="$(date +%Y%m%d-%H%M%S)"
DIR="backups/$TS"
mkdir -p "$DIR"

# shellcheck disable=SC1090
set -a && . "$ENVFILE" && set +a

echo "==> 备份数据库 → $DIR/db.sql.gz"
docker compose -f "$COMPOSE" --env-file "$ENVFILE" exec -T postgres \
  pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" | gzip > "$DIR/db.sql.gz"

echo "==> 备份配置 → $DIR/config.tar.gz"
tar -czf "$DIR/config.tar.gz" config/.env 2>/dev/null || true

ln -sfn "$TS" backups/latest
echo "✅ 备份完成：$DIR （backups/latest 指向它）"
