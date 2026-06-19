# 网关镜像。注意：构建上下文应为仓库根（需要 COPY packages/py-common）。
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir uv
# 先装共享库与第三方依赖
COPY packages/py-common /opt/py-common
RUN uv pip install --system --no-cache fastapi "uvicorn[standard]" pydantic-settings httpx /opt/py-common
# 再拷应用与路由表
COPY services/gateway/app ./app
COPY services/gateway/routes.json ./routes.json
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
