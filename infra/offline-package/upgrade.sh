#!/usr/bin/env bash
# 院内升级：./upgrade.sh v1.4.0  —— 先备份，健康检查失败自动回滚到上一版本。
# 单容器方案：导入新镜像 → 重启 app（容器内自动向后兼容迁移）→ 健康检查。
set -euo pipefail
NEW_TAG="${1:?用法: ./upgrade.sh <版本号，如 v1.4.0>}"
PREV_TAG="$(cat .current_version 2>/dev/null || echo "${TAG:-unknown}")"
COMPOSE="compose/docker-compose.prod.yml"
ENVFILE="config/.env"

rollback() {
  echo "!! 升级失败，回滚到 $PREV_TAG"
  bash restore.sh --latest || echo "!! 自动恢复失败，请手动 ./restore.sh"
  TAG="$PREV_TAG" docker compose -f "$COMPOSE" --env-file "$ENVFILE" up -d app
  exit 1
}
trap rollback ERR

echo "==> [1/4] 备份数据库 + 配置"
bash backup.sh

echo "==> [2/4] 导入新镜像 ($NEW_TAG)"
for f in images/*.tar; do docker load -i "$f"; done

echo "==> [3/4] 重启 app（容器内 alembic upgrade，向后兼容、可重入）"
TAG="$NEW_TAG" docker compose -f "$COMPOSE" --env-file "$ENVFILE" up -d --no-deps app

echo "==> [4/4] 健康检查"
bash healthcheck.sh

echo "$NEW_TAG" > .current_version
trap - ERR
echo "✅ 升级到 $NEW_TAG 完成"
