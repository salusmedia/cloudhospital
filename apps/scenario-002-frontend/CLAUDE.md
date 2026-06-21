# CLAUDE.md · 场景 002 frontend · 家庭病床

## 场景信息
- 编号：scenario-002
- 名称：家庭病床管理
- 部分：前端 (Next.js 14, App Router)
- 一句话：护士/医生在院外为居家患者建床、审核准入、监测体征、分派护理任务、最终办理出院结算。

## 核心业务流程
1. 医护人员登录后进入候诊看板，查看全部病床状态。
2. 申请建床（`POST /beds`）→ 状态进入 `reviewing`（待审核）。
3. 科室负责人审核准入（`POST /beds/{no}/review`）→ 通过则 `admitted`。
4. 在床期间，持续监测体征（从 `platform_iot` 取值）、指派并完成护理任务。
5. 出院结算（`POST /beds/{no}/discharge`）→ 调 platform_clearing 计费分账。

## 页面结构
- `page.tsx`：单页，分左（床位列表 + 看板统计）右（选中床的详情：体征/任务/操作）。
- `homebed-api.ts`：全部 HTTP 调用封装（不在页面里裸用 fetch）。

## 依赖的平台能力
- 登录鉴权：platform-auth（网关注入身份）
- IoT 体征：platform-iot（通过 scenario-002-backend 的 /beds/{no}/monitor 透出）
- 调接口统一用 @hospital/sdk；组件用 @hospital/ui

## 对外暴露的接口（后端）
- 路径前缀：/api/scenario-002
- GET /beds、POST /beds、POST /beds/{no}/review
- GET /beds/{no}/monitor、GET /beds/{no}/tasks、POST /tasks/{id}/done
- POST /beds/{no}/discharge、GET /dashboard、GET /quality

## 合规要求
- 患者敏感数据不写 console.log、不存 localStorage（只存 token）。
- 每次操作后刷新列表，确保页面与后端状态同步。

## 不要做的事
- ❌ 不要在前端自己计算分账/费用——走 discharge 接口。
- ❌ 不要直接 import 其他 scenario-* 的代码。
