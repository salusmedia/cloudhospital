# 单容器镜像：统一网关 + 全部平台服务/场景后端 + 聚合前端（portal + 各 Next 静态导出）。
# 仅用于 Railway 等公有云的【演示】部署（纯模拟数据）。
# 生产私有化部署仍走 infra/offline-package 的离线多镜像方案（数据不出院）。

# ========== 阶段 1：前端构建（Node 编译所有 Next 应用为静态导出）==========
FROM node:20-slim AS web-builder
RUN corepack enable && corepack prepare pnpm@9.15.9 --activate
WORKDIR /build

# 先拷 workspace 清单 + 共享包 + 各前端，安装依赖（利用缓存）
COPY pnpm-workspace.yaml package.json pnpm-lock.yaml ./
COPY turbo.json ./
COPY packages ./packages
COPY apps ./apps
RUN pnpm install --frozen-lockfile

# 构建 6 个 Next 应用（output:export → 各自 out/ 静态产物）
RUN pnpm --filter "./apps/*" build

# 装配统一 web 根：portal 静态站在根，各 Next 导出按 basePath 落子目录
RUN mkdir -p /web && cp -r apps/portal/. /web/ && \
    cp -r apps/scenario-001-frontend/out /web/scenario-001 && \
    cp -r apps/scenario-002-frontend/out /web/scenario-002 && \
    cp -r apps/scenario-006-frontend/out /web/scenario-006 && \
    cp -r apps/scenario-019-frontend/out /web/scenario-019 && \
    cp -r apps/patient-portal/out        /web/patient && \
    cp -r apps/regulator-portal/out      /web/regulator

# ========== 阶段 2：运行镜像（Python 网关 + 后端，Node 不进最终镜像）==========
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

# python:3.12-slim 已自带 bash/ca-certificates；所有依赖均有 wheel，无需编译工具链。
RUN pip install --no-cache-dir uv

WORKDIR /app
COPY . /app

# 安装整个 uv workspace 的依赖 + 迁移工具(db 依赖组)到 /app/.venv
RUN uv sync --group db
ENV PATH="/app/.venv/bin:$PATH"

# 从前端构建阶段拷入装配好的聚合 web 根（网关 GATEWAY_WEB_ROOT=/app/web）
COPY --from=web-builder /web /app/web

EXPOSE 8080
# 场景 backend 端口已移至 18001-18019，网关监听 $PORT（Railway 自动分配）
CMD ["bash", "scripts/start-container.sh"]
