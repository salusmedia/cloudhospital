#!/usr/bin/env bash
# 从备份恢复数据库。用法：
#   ./restore.sh --latest           恢复最近一次备份
#   ./restore.sh backups/<时间戳>    恢复指定备份目录
set -euo pipefail
COMPOSE="compose/docker-compose.prod.yml"
ENVFILE="config/.env"

if [ "${1:-}" = "--latest" ]; then
  DIR="backups/$(readlink backups/latest 2>/dev/null || true)"
  [ -d "$DIR" ] || DIR="backups/latest"
else
  DIR="${1:?用法: ./restore.sh --latest | ./restore.sh backups/<时间戳>}"
fi
[ -f "$DIR/db.sql.gz" ] || { echo "找不到备份文件 $DIR/db.sql.gz"; exit 1; }

# shellcheck disable=SC1090
set -a && . "$ENVFILE" && set +a

echo "==> 从 $DIR 恢复数据库（将覆盖当前数据）"
gunzip -c "$DIR/db.sql.gz" | docker compose -f "$COMPOSE" --env-file "$ENVFILE" exec -T postgres \
  psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}"
echo "✅ 恢复完成（来源 $DIR）"
