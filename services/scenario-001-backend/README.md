# 场景 001 · 在线随访

- 负责人：owner-001
- 前端：`apps/scenario-001-frontend`（端口 3001）
- 后端：`services/scenario-001-backend`（端口 8001，前缀 `/api/scenario-001`）

## 本地起这个场景
```bash
pnpm run dev --filter=scenario-001-*
# 后端单独起：cd services/scenario-001-backend && uv run uvicorn app.main:app --reload --port 8001
```

开发规范见本目录 `CLAUDE.md` 与仓库 `docs/04-应用场景开发流程.md`。
