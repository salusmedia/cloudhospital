# CLAUDE.md · 场景 019 frontend · 转诊一件事

## 场景信息
- 编号：scenario-019
- 名称：转诊一件事
- 部分：前端 (Next.js 14, App Router)
- 一句话：展示转诊全流程：发起转诊、接收转诊（4方分账）、七节点积分链、个人服务信用账户。

## 核心业务流程
1. 医生（referral:initiate）点"发起转诊"填写患者 ID / 类型 / 风险等级 → `POST /referrals`。
2. 接收医生（referral:receive）在列表选中申请中转诊单 → 点"接收转诊" → `POST /referrals/{no}/receive`。
3. 接收成功后显示 4 方分账明细（individual/dept/org/platform）和金额。
4. 七节点进度面板：逐节点点"完成"→ `POST /referrals/{no}/nodes/{node}/complete` → 积分实时更新。
5. 信用账户卡片展示累计积分和可兑现金额（最近 5 条流水）。

## 页面结构
- `page.tsx`：单页，顶部信用账户 pill + 发起转诊折叠表单，左列转诊列表，右列详情/分账/节点/账户。
- `referral-api.ts`：全部 HTTP 调用封装（listReferrals/createReferral/receiveReferral/listNodes/completeNode/getCreditAccount）。

## 依赖的平台能力
- 登录鉴权：platform-auth（网关注入，token 存 localStorage）
- 调接口统一用 @hospital/sdk；组件用 @hospital/ui

## 不要做的事
- ❌ 不要在前端存患者主数据或分账金额到 localStorage。
- ❌ 不要绕开 scenario-019-backend 直接调分账平台接口。
