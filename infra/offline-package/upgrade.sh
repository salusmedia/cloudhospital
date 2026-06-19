#!/usr/bin/env bash
# 院内升级：./upgrade.sh v1.4.0  —— 先备份，迁移失败/健康检查失败自动回滚。
set -euo pipefail
NEW_TAG="${1:?用法: ./upgrade.sh <版本号，如 v1.4.0>}"
PREV_TAG="$(cat .current_version 2>/dev/null || echo unknown)"
COMPOSE="compose/docker-compose.prod.yml"
ENVFILE="config/.env"

rollback() {
  echo "!! 升级失败，回滚到 $PREV_TAG"
  bash restore.sh --latest
  TAG="$PREV_TAG" docker compose -f "$COMPOSE" --env-file "$ENVFILE" up -d
  exit 1
}
trap rollback ERR

echo "==> [1/5] 备份数据（数据库 + 对象存储 + 配置）"
bash backup.sh

echo "==> [2/5] 导入新镜像 ($NEW_TAG)"
for f in images/*.tar; do docker load -i "$f"; done

echo "==> [3/5] 数据库迁移（向后兼容、可重入）"
TAG="$NEW_TAG" docker compose -f "$COMPOSE" --env-file "$ENVFILE" run --rm platform-auth alembic upgrade head

echo "==> [4/5] 滚动重启（网关最后切）"
TAG="$NEW_TAG" docker compose -f "$COMPOSE" --env-file "$ENVFILE" up -d --no-deps \
  platform-auth platform-patient $(grep -o 'scenario-[0-9]*-backend' "$COMPOSE" | sort -u) web
TAG="$NEW_TAG" docker compose -f "$COMPOSE" --env-file "$ENVFILE" up -d --no-deps gateway nginx

echo "==> [5/5] 健康检查"
bash healthcheck.sh

echo "$NEW_TAG" > .current_version
trap - ERR
echo "✅ 升级到 $NEW_TAG 完成"
