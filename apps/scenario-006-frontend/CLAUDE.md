# CLAUDE.md · 场景 006 frontend · 在线复诊

## 场景信息
- 编号：scenario-006
- 名称：在线复诊（互联网诊疗）
- 部分：前端 (Next.js 14, App Router)
- 一句话：医生在线接诊慢病/复诊患者，开具电子处方并由 platform-ai 实时审方，完成后自动计费分账。

## 核心业务流程
1. 候诊队列：患者通过居民端（portal）发起复诊申请，医生在此页面看到候诊列表（`waiting`）。
2. 接诊（`POST /consults/{no}/accept`）→ 状态变 `in_progress`，患者与医生进入诊室。
3. 开具处方（`POST /consults/{no}/prescribe`）→ 后端同步调 platform-ai/rx-review 做 AI 审方。
4. 前端展示审方结果（passed/warn/rejected），warn 级别医生可继续，rejected 需换药。
5. 结束诊次（`POST /consults/{no}/finish`）→ 调 platform_clearing 计费，返回分账明细。

## 页面结构
- `page.tsx`：单页，左列候诊队列，右列接诊详情（含开方表单 + AI 审方结果展示 + 结算摘要）。
- `teleconsult-api.ts`：全部 HTTP 调用封装。

## AI 审方说明
- 后端 scenario-006 的 `/prescribe` 接口会调 `platform-ai/rx-review`。
- platform-ai 配置 `ANTHROPIC_API_KEY` 时调用 Claude Haiku；否则降级到规则引擎。
- 前端通过 `rx.ai_review`（passed/warn/rejected）和 `rx.review_note` 展示结果。

## 依赖的平台能力
- 登录鉴权：platform-auth（网关注入）
- AI 审方：platform-ai（由 scenario-006-backend 代理调用）
- 调接口统一用 @hospital/sdk；组件用 @hospital/ui

## 合规要求
- 不在前端打印患者主诉等敏感字段。
- AI 审方结果是辅助意见，最终决策权在医生（前端展示时需有该说明）。

## 不要做的事
- ❌ 不要在前端直接调 platform-ai——走 scenario-006-backend 的 prescribe 接口。
- ❌ 不要自行缓存患者数据到 localStorage。
