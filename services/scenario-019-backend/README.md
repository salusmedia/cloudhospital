# 场景 019 · 转诊一件事

- 负责人：owner-019
- 前端：`apps/scenario-019-frontend`（端口 3019）
- 后端：`services/scenario-019-backend`（端口 8019，前缀 `/api/scenario-019`）

## 本地起这个场景
```bash
pnpm run dev --filter=scenario-019-*
# 后端单独起：cd services/scenario-019-backend && uv run uvicorn app.main:app --reload --port 8019
```

开发规范见本目录 `CLAUDE.md` 与仓库 `docs/04-应用场景开发流程.md`。
