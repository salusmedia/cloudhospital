#!/usr/bin/env bash
# 院内首次安装。在离线包解压目录内执行：./install.sh
# 单容器方案：导入镜像 → 起 PostgreSQL → 起 app（自动迁移；SEED_DEMO=false 不灌演示数据）。
set -euo pipefail
COMPOSE="compose/docker-compose.prod.yml"
ENVFILE="config/.env"

echo "==> [1/4] 环境检查"
command -v docker >/dev/null || { echo "缺少 docker"; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "缺少 docker compose v2"; exit 1; }
[ -f "$ENVFILE" ] || { echo "请先 cp config/.env.example config/.env 并填写"; exit 1; }
# 镜像坐标（REGISTRY/TAG）来自构建期写入的 .image.env
[ -f config/.image.env ] && set -a && . config/.image.env && set +a

echo "==> [2/4] 导入镜像"
for f in images/*.tar; do echo "  load $f"; docker load -i "$f"; done

echo "==> [3/4] 启动 PostgreSQL 并等待就绪"
docker compose -f "$COMPOSE" --env-file "$ENVFILE" up -d postgres
bash healthcheck.sh --wait-db

echo "==> [4/4] 启动 app（容器内自动 alembic 迁移）"
docker compose -f "$COMPOSE" --env-file "$ENVFILE" up -d app
bash healthcheck.sh

echo "✅ 安装完成。访问 http://<本机IP>:${PUBLIC_PORT:-8080}/  （健康检查 /health）"
echo "   生产请确认 .env 中 SEED_DEMO=false（不灌演示患者数据）。"
