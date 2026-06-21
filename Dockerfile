# 单容器镜像：统一网关 + 全部平台服务/场景后端 + 静态门户。
# 仅用于 Railway 等公有云的【演示】部署（纯模拟数据）。
# 生产私有化部署仍走 infra/offline-package 的离线多镜像方案（数据不出院）。
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

EXPOSE 8080
# 场景 backend 端口已移至 18001-18019，网关监听 $PORT（Railway 自动分配）
CMD ["bash", "scripts/start-container.sh"]
