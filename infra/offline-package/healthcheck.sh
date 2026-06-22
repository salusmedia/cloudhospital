#!/usr/bin/env bash
# 健康检查。用法：
#   ./healthcheck.sh            检查 app /health
#   ./healthcheck.sh --wait-db  等待 PostgreSQL 就绪（安装时用）
set -euo pipefail
COMPOSE="compose/docker-compose.prod.yml"
ENVFILE="config/.env"
PORT="$(grep -E '^PUBLIC_PORT=' "$ENVFILE" 2>/dev/null | cut -d= -f2 || true)"
PORT="${PORT:-8080}"

wait_db() {
  echo "  等待 PostgreSQL ..."
  for i in $(seq 1 30); do
    if docker compose -f "$COMPOSE" --env-file "$ENVFILE" exec -T postgres pg_isready >/dev/null 2>&1; then
      echo "  ✓ PostgreSQL 就绪"; return 0
    fi
    sleep 2
  done
  echo "  ✗ PostgreSQL 30 次重试仍未就绪"; return 1
}

check_app() {
  echo "  检查 app /health ..."
  for i in $(seq 1 60); do
    if curl -fsS "http://localhost:${PORT}/health" >/dev/null 2>&1; then
      echo "  ✓ app 健康（http://localhost:${PORT}/health）"; return 0
    fi
    sleep 3
  done
  echo "  ✗ app 180s 内未通过健康检查，查看日志：docker compose -f $COMPOSE logs app"
  return 1
}

case "${1:-}" in
  --wait-db) wait_db ;;
  *)         check_app ;;
esac
