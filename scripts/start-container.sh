#!/usr/bin/env bash
# 单容器入口（Railway 演示部署）：迁移 + 种子 + 起全部后端(localhost) + 网关绑 $PORT。
# 所有服务跑在同一容器内，网关用 USE_LOCALHOST=true 经 localhost 互联。
set -euo pipefail
cd /app

# ---- 数据库连接串：Railway Postgres 注入 DATABASE_URL（postgres:// 或 postgresql://）----
RAW_DB="${DATABASE_URL:?需要 DATABASE_URL（在 Railway 加 PostgreSQL 插件后自动注入）}"
# SQLAlchemy 需要 +psycopg 方言；psycopg.connect（种子脚本）用原始 libpq URL。
SA_DB="$(printf '%s' "$RAW_DB" | sed -E 's#^postgres(ql)?://#postgresql+psycopg://#')"

JWT="${JWT_SECRET:-dev-demo-secret-change-me}"
PII="${PII_KEY:-dev-demo-pii-key-change-me}"

export DATABASE_URL="$SA_DB"          # alembic env.py 用
export SEED_DB="$RAW_DB"              # seed_external.py（psycopg.connect）用
export PLATFORM_AUTH_JWT_SECRET="$JWT" GATEWAY_JWT_SECRET="$JWT"
export PLATFORM_PATIENT_PII_KEY="$PII"
export GATEWAY_USE_LOCALHOST=true
export GATEWAY_WEB_ROOT=/app/apps/portal
for s in PLATFORM_AUTH PLATFORM_PATIENT PLATFORM_ARCHIVE PLATFORM_IOT PLATFORM_CONSENT PLATFORM_FILE SCENARIO_001 SCENARIO_002 SCENARIO_006 SCENARIO_019; do
  export "${s}_DATABASE_URL=$SA_DB"
done

echo ">> alembic upgrade head"
( cd infra/db && alembic upgrade head )

echo ">> seed demo data（幂等，纯模拟数据）"
python scripts/seed_external.py || echo "!! seed 跳过/失败（非致命，继续）"

# ---- 起全部后端（仅监听 127.0.0.1；端口须与网关 routing.py / routes.json 对齐）----
run() { ( cd "$1" && exec python -m uvicorn app.main:app --host 127.0.0.1 --port "$2" --log-level warning ) & }
run services/platform-auth      8101
run services/platform-patient   8102
run services/platform-file      8104
run services/platform-archive   8105
run services/platform-iot       8106
run services/platform-consent   8107
run services/scenario-001-backend 8001
run services/scenario-002-backend 8002
run services/scenario-006-backend 8006
run services/scenario-019-backend 8019

# 等后端起好，再前台起网关（绑 Railway 的 $PORT）
sleep 6
echo ">> gateway 监听 0.0.0.0:${PORT:-8080}"
cd services/gateway
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8080}"
