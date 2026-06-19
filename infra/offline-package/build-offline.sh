#!/usr/bin/env bash
# 由 CI 在外网/内网构建机执行：拉取某 tag 的全部镜像，导出成离线安装包。
# 用法: build-offline.sh <REGISTRY> <TAG>
set -euo pipefail
REGISTRY="${1:?}"; TAG="${2:?}"
OUT="dist/ai-hospital-${TAG}"
rm -rf "$OUT" && mkdir -p "$OUT/images" "$OUT/compose" "$OUT/config"

# 本平台所有服务列表（新增场景时在此登记，或从 build-manifest.txt 读取）
SERVICES=(gateway platform-auth platform-patient platform-ai platform-file web scenario-001-backend)
THIRD_PARTY=(postgres:16 redis:7 minio/minio nginx:1.27)

echo "==> 拉取并导出业务镜像"
for s in "${SERVICES[@]}"; do
  docker pull "$REGISTRY/$s:$TAG"
  docker save "$REGISTRY/$s:$TAG" -o "$OUT/images/$s.tar"
done
echo "==> 拉取并导出第三方镜像"
for i in "${THIRD_PARTY[@]}"; do
  docker pull "$i"; docker save "$i" -o "$OUT/images/$(echo "$i" | tr '/:' '__').tar"
done

echo "==> 拷贝编排/配置/脚本/手册"
cp infra/offline-package/docker-compose.prod.yml "$OUT/compose/"
cp infra/offline-package/{install.sh,upgrade.sh,backup.sh,restore.sh,healthcheck.sh} "$OUT/" 2>/dev/null || true
cp infra/offline-package/.env.example "$OUT/config/" 2>/dev/null || true
cp -r infra/offline-package/nginx "$OUT/config/" 2>/dev/null || true
cp -r services/*/migrations "$OUT/migrations/" 2>/dev/null || true
cp CHANGELOG.md "$OUT/" 2>/dev/null || true
echo "REGISTRY=$REGISTRY" > "$OUT/config/.env.example.registry"
echo "TAG=$TAG" >> "$OUT/config/.env.example.registry"

echo "==> 打包"
tar -czf "dist/ai-hospital-${TAG}.tar.gz" -C dist "ai-hospital-${TAG}"
echo "✅ 生成 dist/ai-hospital-${TAG}.tar.gz"
