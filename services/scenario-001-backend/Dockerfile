# 场景 001 后端镜像。由 CI 构建，离线包导入院内。
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY services/scenario-001-backend/pyproject.toml ./
RUN uv pip install --system --no-cache .
COPY services/scenario-001-backend/app ./app
EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
