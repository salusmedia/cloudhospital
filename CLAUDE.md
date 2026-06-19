# CLAUDE.md · 根级规范（人与 Claude Code 共同遵守）

本文件是全仓最高规范。Claude Code 会自动读取本文件，以及你所在目录链上的所有 `CLAUDE.md`（越靠近越具体）。

## 这个项目是什么
AI 云医院平台。Monorepo 管理多个**编号应用场景**（前端 TS/Next.js + 后端 Python/FastAPI），
场景之间通过共享库与平台服务相互关联，最终容器化、私有化部署到**院内**（数据不出院）。

完整体系见 `docs/`（先读 `docs/00-开发体系总纲.md`）。

## 目录与边界（强约束）
- 场景前端：`apps/scenario-XXX-frontend/`；场景后端：`services/scenario-XXX-backend/`。
- 共享代码：`packages/`（types/ui/sdk/config/py-common）。平台服务：`services/platform-*`、`services/gateway`。
- **依赖规则**：场景只能依赖 `packages/` 和平台服务（走 HTTP/网关）。
  - ❌ 禁止：一个场景直接 import 另一个场景的代码。
  - ❌ 禁止：`packages/` 反向依赖场景。
  - 需要别的场景的数据/能力 → 走平台服务或对方 HTTP API；需要共享类型 → 放 `packages/shared-types`。

## 编码规范
- 前端：TypeScript 严格模式；组件优先复用 `packages/ui`；调接口统一用 `packages/sdk`。
- 后端：FastAPI；鉴权/日志/审计/DB 基类统一用 `packages/py-common`；类型注解 + 通过 mypy。
- 风格交给工具：前端 ESLint/Prettier，后端 Ruff。不要手动纠风格，跑 `pnpm run check`。
- 接口改动后必须 `pnpm run gen:types` 同步共享类型。

## 医疗合规（不可妥协）
- 患者敏感数据（身份证、手机号、病历、诊断）**禁止写入日志、禁止进提交记录、禁止喂给 AI 对话**。
- 每个接口必须鉴权 + 数据权限校验（最小权限）。
- 患者数据的增删改查必须落审计日志（用 `py-common` 审计中间件）。
- 密钥/配置不进仓库、不进镜像，运行时由环境注入。

## 测试与质量
- 新增/改动核心逻辑必须有测试；场景核心覆盖率 ≥ 80%。
- 提交前本地必须 `pnpm run check`（lint+typecheck+test）全绿。

## 与 Claude Code 协作的约定
- **小步**：一次做一件事，每步给出 diff 供人 review。
- **危险操作人来确认**：`git push`、合并 MR、删分支、删数据、对外发布——**不要自动执行**，先征求确认。
- 不确定业务时，先读对应场景的 `CLAUDE.md` 和 `docs/`，再动手；仍不确定就提问。
- 复杂改动先给计划，确认后再改。

## 提交与分支
- 分支：`feature|fix|chore/scenario-XXX-描述`。提交：Conventional Commits（`feat(scenario-XXX): ...`）。
- main 受保护，只能走 MR。详见 `docs/03-协作规范-分支与提交.md`。
