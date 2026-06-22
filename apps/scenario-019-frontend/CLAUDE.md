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

## 页面结构（两个标签）
- `page.tsx`：顶部标题 + 标签栏（🔁 转诊协同 / 👥 MDT 会诊），下方按 tab 渲染。
  - `ReferralView`（转诊）：信用账户 pill + 发起转诊折叠表单，左列转诊列表，右列详情/分账/节点/账户。
  - `MdtView.tsx`（MDT 会诊）：左列会诊列表，右列病例/专家/署名意见 + 发起会诊表单。
- `referral-api.ts`：转诊相关 HTTP 封装。
- `mdt-api.ts`：MDT HTTP 封装（listMdt/getMdt/createMdt/submitOpinion）+ `parseExperts` 纯函数。

## MDT 会诊
- 消费 `/scenario-019/mdt`（list/create/get/{id}/opinion）。
- 发起会诊：主题/病例摘要（脱敏）/关联转诊单/专家（每行"姓名,科室,机构"，前端 parseExperts 解析）。
- 专家显示确认状态；意见为署名意见，按时间线展示。

## 依赖的平台能力
- 登录鉴权：platform-auth（网关注入，token 存 localStorage）
- 调接口统一用 @hospital/sdk；组件用 @hospital/ui

## 不要做的事
- ❌ 不要在前端存患者主数据或分账金额到 localStorage。
- ❌ 不要绕开 scenario-019-backend 直接调分账平台接口。
