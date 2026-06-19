#!/usr/bin/env bash
# 院内首次安装。在离线包解压目录内执行：./install.sh
set -euo pipefail

echo "==> [1/5] 环境检查"
command -v docker >/dev/null || { echo "缺少 docker"; exit 1; }
command -v docker compose >/dev/null 2>&1 || docker-compose version >/dev/null || { echo "缺少 docker compose"; exit 1; }
[ -f config/.env ] || { echo "请先 cp config/.env.example config/.env 并填写"; exit 1; }

echo "==> [2/5] 导入镜像"
for f in images/*.tar; do echo "  load $f"; docker load -i "$f"; done

echo "==> [3/5] 启动基础设施 (postgres/redis/minio)"
docker compose -f compose/docker-compose.prod.yml --env-file config/.env up -d postgres redis minio
bash healthcheck.sh --wait-infra

echo "==> [4/5] 数据库迁移"
docker compose -f compose/docker-compose.prod.yml --env-file config/.env run --rm platform-auth alembic upgrade head
# 各服务的迁移按需补充

echo "==> [5/5] 启动全部服务"
docker compose -f compose/docker-compose.prod.yml --env-file config/.env up -d
bash healthcheck.sh

echo "✅ 安装完成。访问地址见 config/.env 中的 PUBLIC_URL"
