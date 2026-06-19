# platform-auth 镜像。构建上下文应为仓库根（需要 COPY packages/py-common）。
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY packages/py-common /opt/py-common
RUN uv pip install --system --no-cache fastapi "uvicorn[standard]" pydantic-settings /opt/py-common
COPY services/platform-auth/app ./app
EXPOSE 8101
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8101"]
