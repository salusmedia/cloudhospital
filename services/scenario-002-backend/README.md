# 场景 002 · 家庭病床

- 负责人：owner-002
- 前端：`apps/scenario-002-frontend`（端口 3002）
- 后端：`services/scenario-002-backend`（端口 8002，前缀 `/api/scenario-002`）

## 本地起这个场景
```bash
pnpm run dev --filter=scenario-002-*
# 后端单独起：cd services/scenario-002-backend && uv run uvicorn app.main:app --reload --port 8002
```

开发规范见本目录 `CLAUDE.md` 与仓库 `docs/04-应用场景开发流程.md`。
