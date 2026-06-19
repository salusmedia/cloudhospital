# 场景 006 · 线上复诊

- 负责人：owner-006
- 前端：`apps/scenario-006-frontend`（端口 3006）
- 后端：`services/scenario-006-backend`（端口 8006，前缀 `/api/scenario-006`）

## 本地起这个场景
```bash
pnpm run dev --filter=scenario-006-*
# 后端单独起：cd services/scenario-006-backend && uv run uvicorn app.main:app --reload --port 8006
```

开发规范见本目录 `CLAUDE.md` 与仓库 `docs/04-应用场景开发流程.md`。
