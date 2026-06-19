# CLAUDE.md · 场景 019 backend · 转诊一件事

## 场景信息
- 编号：scenario-019
- 名称：转诊一件事
- 部分：后端 (FastAPI)
- 负责人：owner-019
- 一句话：基层与上级医院之间的转诊全流程协同，规范转诊计分计酬。

## 核心业务流程
1. 基层医生发起上转，平台智能推荐接收机构。
2. 接收医院接收转诊（`receive`），状态流转，并产生一笔"接收协同服务"收入。
3. 收入按 `platform_clearing.service_rate_card` 计价，`split_income` 4 方分账落库。
4. 七节点完成情况记入个人服务信用账户（后续接 `credit_*`）。

## 依赖的平台能力（必须复用，不要自建）
- 登录鉴权：platform-auth（经网关注入身份）
- 患者档案：platform-patient（HTTP，勿自存患者表）
- 文件/影像：platform-file　|　AI 能力：platform-ai
- 鉴权/日志/审计/脱敏/DB 基类统一用 packages/py-common

## 对外暴露的接口
- 路径前缀：/api/scenario-019
- `GET /referrals`：列转诊单（按 scopes 数据权限过滤）。
- `POST /referrals/{ref_no}/receive`：接收上转（需能力 `referral:receive`），分账落库。

## 领域术语 & 数据模型
- 本场景表在 schema `scenario_referral`（见 infra/db/ddl/03）；ORM 在 `app/models.py`。
- 计价/分账表在平台域 `platform_clearing`，跨 schema 引用，不自建。
- 患者只存 `patient_id` 引用，不自存患者主数据。

## 业务规则与边界
- **数据权限**：所有查询走 `py_common.scope_filter`，禁止裸写 `WHERE dept_code`。
- **场景权限**：能力点用 `py_common.require_cap("referral:receive")`，与全局 RBAC 解耦。
- **分账**：用 `py_common.clearing.split_income`，台账 append-only，金额用 Decimal。
- 接收时校验接收方对该单科室有 scope；缺计价规则应显式报错而非默默不计酬。

## 合规要求（医疗，重点）
- 敏感字段禁止入日志；存储/传输需脱敏或加密。
- 每个接口校验登录 + 数据权限（最小权限）。
- 患者数据增删改查必须落审计日志。

## 测试要求
- 核心逻辑覆盖率 ≥ 80%；必测：空数据、越权、异常输入。
- 提交前：pnpm run check --filter=scenario-019-*

## 不要做的事
- ❌ 不要直接 import 其他 scenario-* 的代码（走共享层或 HTTP）。
- ❌ 不要自存患者/用户主数据。
- ❌ 不要把敏感数据写进日志或提交记录。
- ❌ 改接口后记得让前端 pnpm run gen:types 同步类型。
