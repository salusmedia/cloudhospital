# 场景 CLAUDE.md 模板

> 复制此文件到 `apps/scenario-XXX-frontend/CLAUDE.md` 和 `services/scenario-XXX-backend/CLAUDE.md`，
> 删除本说明行，按实际填写。**填得越具体，Claude Code 写出的代码越贴合业务。**

---

## 场景信息
- **编号**：scenario-XXX
- **名称**：<场景中文名>
- **一句话**：<它解决什么问题、给谁用>
- **负责人**：<姓名>

## 核心业务流程
<用 3~6 步把主流程说清楚，例如：医生发起 → 患者填写 → 系统评估 → 生成报告 → 推送随访>

## 依赖的平台能力（必须复用，不要自建）
- 登录鉴权：`platform-auth`（经网关注入用户身份）
- 患者档案：`platform-patient`（HTTP，勿自存患者表）
- 文件/影像：`platform-file`
- AI 能力：`platform-ai`
- 前端统一调用：`packages/sdk`；共享类型：`packages/shared-types`；UI：`packages/ui`

## 对外暴露的接口
<列出本场景提供给其他场景/前端的主要 API 与路径前缀，例如 /api/scenario-XXX/...>

## 领域术语 & 数据模型
<术语表 + 关键实体字段，标注哪些是敏感字段>

## 业务规则与边界
<特殊规则、状态机、权限规则、易错点>

## 合规要求（医疗，重点）
- 敏感字段：<如身份证、手机号、诊断结果> —— **禁止入日志**，存储/传输需脱敏或加密。
- 鉴权：每个接口校验登录 + 数据权限（只能访问自己有权的患者）。
- 审计：对患者数据的增删改查必须落审计日志（用 `py-common` 审计中间件）。

## 测试要求
- 单测覆盖核心业务逻辑 ≥ 80%；必测：空数据、越权、异常输入。
- 提交前跑 `pnpm run check --filter=scenario-XXX-*`。

## 不要做的事
- ❌ 不要直接 import 其他 `scenario-*` 的代码。
- ❌ 不要自己存患者/用户主数据。
- ❌ 不要把敏感数据写进日志或提交记录。
- ❌ 改接口不要忘了 `pnpm run gen:types`。
