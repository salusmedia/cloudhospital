# CLAUDE.md · 场景 001 frontend · 在线随访

## 场景信息
- 编号：scenario-001
- 名称：在线随访
- 部分：前端 (Next.js 14, App Router, basePath /scenario-001)
- 负责人：owner-001
- 一句话：医护按科室权限查看随访计划与随访记录、按日期筛选、新增随访记录。

## 核心业务流程
1. 进入页面自动加载本科室随访计划（`GET /plans`）+ 随访记录（`GET /followups`）。
2. 左列展示随访计划（慢病/出院/肿瘤，含随访间隔与起止日期）。
3. 右列展示随访记录，可按随访日期筛选（`?on=YYYY-MM-DD`）。
4. 点"新增随访记录"填患者/日期/方式/备注/下次日期 → `POST /followups`，保存后自动刷新。

## 页面结构
- `page.tsx`：单页双列（左随访计划 + 右随访记录），顶部新增折叠表单。
- `followup-api.ts`：HTTP 封装（listPlans / listFollowups / createFollowup + 导出 buildFollowupQuery 供单测）。
- `followup-api.test.ts`：buildFollowupQuery 查询串构造的单元测试（6 例）。

## 依赖的平台能力（必须复用，不要自建）
- 登录鉴权：platform-auth（经网关注入身份；token 存 localStorage）
- 患者档案：platform-patient（HTTP，勿自存患者表）
- 调后端统一用 @hospital/sdk；组件用 @hospital/ui

## 对外暴露的接口
- 路径前缀：/api/scenario-001
- `GET /plans` — 随访计划列表（scope_filter 按科室）
- `GET /followups?on=&dept=&page=` — 随访记录分页
- `POST /followups` — 新增随访记录（patient_id/visit_date/method/note/next_date/plan_no）

## 领域术语 & 数据模型
- 随访计划 followup_plan：plan_type(chronic/discharge/tumor)、interval_days、start/end_date。
- 随访记录 followup_record：method(phone/video/onsite)、visit_date、next_date、note。
- 字段与后端一致用 snake_case；只持 patient_id 引用，**不**自存患者主数据。

## 业务规则与边界
- 数据按 dept_code 科室权限过滤（后端 scope_filter）；前端不做越权展示。
- 字段命名跟随后端裸载荷（snake_case），不要再套 camelCase 映射。

## 合规要求（医疗，重点）
- 敏感字段禁止入日志；存储/传输需脱敏或加密。
- 每个接口校验登录 + 数据权限（最小权限）。
- 患者数据增删改查必须落审计日志。

## 测试要求
- 核心逻辑覆盖率 ≥ 80%；必测：空数据、越权、异常输入。
- 提交前：pnpm run check --filter=scenario-001-*

## 不要做的事
- ❌ 不要直接 import 其他 scenario-* 的代码（走共享层或 HTTP）。
- ❌ 不要自存患者/用户主数据。
- ❌ 不要把敏感数据写进日志或提交记录。
- ❌ 后端接口变更后记得 pnpm run gen:types 再用新类型。
