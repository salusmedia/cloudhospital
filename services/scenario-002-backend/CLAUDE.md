# CLAUDE.md · 场景 002 backend · 家庭病床

## 场景信息
- 编号：scenario-002
- 名称：家庭病床管理
- 部分：后端 (FastAPI)
- 一句话：为失能/术后患者在居家环境建立连续护理通道；医护远程管床、发派护理任务、监测体征、最终计费出院。

## 核心业务流程
1. 医护提交建床申请（`POST /beds`）→ 状态 `reviewing`。
2. 科室负责人审核准入（`POST /beds/{no}/review`）→ `admitted` 或 `rejected`。
3. 护士发起护理任务（`POST /beds/{no}/tasks`），完成后更新（`POST /tasks/{id}/done`）。
4. 医生查看体征监测（`GET /beds/{no}/monitor`）→ 复用 `platform_iot` 实时体征 + 异常预警。
5. 出院结算（`POST /beds/{no}/discharge`）→ 复用 `platform_clearing` 计费分账。

## 数据模型（schema: scenario_homebed）
- `bed`：病床主记录（状态机 reviewing → admitted → discharged / rejected）。
- `care_task`：护理任务（体征采集/查房/送药）。
- `bed_message`：医患沟通消息（患者主诉 + 医生回复）。

## 依赖的平台能力
- 登录鉴权：platform-auth（网关注入身份）
- IoT 体征：`platform_iot.vital_sign`（原始 SQL 跨 schema 读）
- 计费分账：`platform_clearing.service_rate_card / income_event / income_split`
- 鉴权/审计/DB：packages/py-common（写接口用 `require_cap("homebed:manage")`）

## 对外暴露的接口（路径前缀 /api/scenario-002）
- `POST /beds` — 建床申请
- `POST /beds/{no}/review` — 准入审核
- `GET /beds` — 病床列表（?status=）
- `GET /beds/{no}/monitor` — 实时体征监测
- `GET /beds/{no}/tasks` — 护理任务列表
- `POST /beds/{no}/tasks` — 新增护理任务
- `POST /tasks/{id}/done` — 完成护理任务
- `POST /beds/{no}/discharge` — 出院结算
- `GET /dashboard` — 病床看板统计
- `GET /quality` — 护理质量指标
- `GET/POST /beds/{no}/messages` — 医患消息

## 合规要求
- 只存 `patient_id` 引用，不自建患者表。
- 写操作必须落 audit_action（含 patient_id）。
- 计费金额从 `platform_clearing.service_rate_card` 动态取，不写死。

## 不要做的事
- ❌ 不要直接 import 其他 scenario-* 代码。
- ❌ 不要自存患者主数据。
- ❌ 不要硬编码计费金额——走平台计价规则表。
- ❌ 不要把敏感数据写进日志。
