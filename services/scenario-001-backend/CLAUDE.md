# CLAUDE.md · 场景 001 backend · 在线随访

## 场景信息
- 编号：scenario-001
- 名称：在线随访
- 部分：后端 (FastAPI)
- 一句话：管理出院/慢病患者的随访计划与随访记录，医生可按科室权限查询并新增随访记录。

## 核心业务流程
1. 医生登录 → 查询本科室随访记录（`GET /followups`，按 `dept_code` 权限过滤）。
2. 查看单条记录详情（`GET /followups/{id}`，越权返回 403）。
3. 新增随访记录（`POST /followups`，记录随访方式/备注/下次日期）。
4. 查询随访计划列表（`GET /plans`，支持按 patient_id 过滤）。

## 数据模型（schema: scenario_followup）
- `followup_plan`：随访计划（慢病/出院/肿瘤），含随访间隔天数与起止日期。
- `followup_record`：具体随访记录，方式（电话/视频/面访）+ 备注 + 下次随访日期。
- 两者均只存 `patient_id` 引用；患者姓名从 `platform-patient` 按需查询。

## 依赖的平台能力
- 登录鉴权：platform-auth（经网关注入 X-User-* 头）
- 患者档案：platform-patient（勿自存患者表）
- 鉴权/审计/DB 基类：packages/py-common
- scope_filter：按 `dept_code` 隔离科室数据

## 对外暴露的接口
- 路径前缀：`/api/scenario-001`
- `GET /followups` — 随访记录分页列表（?on=日期&dept=科室代码）
- `GET /followups/{id}` — 单条随访记录
- `POST /followups` — 新增随访记录
- `GET /plans` — 随访计划列表（?patient_id=）

## 合规要求
- 患者姓名等敏感字段不写日志、不出现在错误响应里。
- 每个接口校验登录 + 数据权限（scope_filter + has_global_scope）。
- 写操作必须落 audit_action。

## 不要做的事
- ❌ 不要在本场景自建患者表——patient_id 引用即可。
- ❌ 不要把敏感字段写入日志。
- ❌ 接口变更后记得同步 apps/scenario-001-frontend 里的 API 客户端。
