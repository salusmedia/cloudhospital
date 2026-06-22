#!/usr/bin/env bash
# 由 CI 在外网/内网构建机执行：构建/拉取单容器镜像 + 第三方镜像，导出成离线安装包。
# 用法: build-offline.sh <REGISTRY> <TAG>
#
# 架构说明：本平台院内部署采用【单容器镜像】方案（与 Railway 演示同一个 Dockerfile）——
# 一个镜像内含 网关 + 全部平台服务/场景后端 + 聚合前端，配 PostgreSQL 即可运行。
# 这样离线包只需导出 2 个镜像，院内运维最简。生产环境置 SEED_DEMO=false 不灌演示数据。
set -euo pipefail
REGISTRY="${1:?用法: build-offline.sh <REGISTRY> <TAG>}"
TAG="${2:?用法: build-offline.sh <REGISTRY> <TAG>}"
OUT="dist/ai-hospital-${TAG}"
rm -rf "$OUT" && mkdir -p "$OUT/images" "$OUT/compose" "$OUT/config"

APP_IMAGE="${REGISTRY}/ai-hospital:${TAG}"
THIRD_PARTY=(postgres:16)

echo "==> 构建应用镜像 $APP_IMAGE（单容器：网关+后端+前端）"
docker build -t "$APP_IMAGE" .
docker save "$APP_IMAGE" -o "$OUT/images/ai-hospital.tar"

echo "==> 拉取并导出第三方镜像"
for i in "${THIRD_PARTY[@]}"; do
  docker pull "$i"
  docker save "$i" -o "$OUT/images/$(echo "$i" | tr '/:' '__').tar"
done

echo "==> 拷贝编排/配置/运维脚本"
cp infra/offline-package/docker-compose.prod.yml "$OUT/compose/"
cp infra/offline-package/{install.sh,upgrade.sh,backup.sh,restore.sh,healthcheck.sh} "$OUT/"
cp infra/offline-package/.env.example "$OUT/config/"
cp DEPLOY.md "$OUT/" 2>/dev/null || true
cp CHANGELOG.md "$OUT/" 2>/dev/null || true
{ echo "REGISTRY=$REGISTRY"; echo "TAG=$TAG"; } > "$OUT/config/.image.env"

echo "==> 打包"
tar -czf "dist/ai-hospital-${TAG}.tar.gz" -C dist "ai-hospital-${TAG}"
echo "✅ 生成 dist/ai-hospital-${TAG}.tar.gz"
echo "   院内：解压 → cp config/.env.example config/.env 填写 → ./install.sh"
