# CLAUDE.md · 场景 006 backend · 在线复诊

## 场景信息
- 编号：scenario-006
- 名称：在线复诊（互联网诊疗）
- 部分：后端 (FastAPI)
- 一句话：慢病/随访患者通过网络发起复诊，医生在线接诊、开具处方（AI 实时审方），诊后自动计费分账。

## 核心业务流程
1. 患者在居民端发起复诊申请 → 系统创建 `consult`（status=`waiting`）。
2. 医生查看候诊队列（`GET /consults`），按科室权限过滤。
3. 接诊（`POST /consults/{no}/accept`）→ status 变 `in_progress`。
4. 开具处方（`POST /consults/{no}/prescribe`）→ 后端调 `platform-ai/rx-review` 实时审方：
   - `passed`：直接保存。
   - `warn`：返回预警，医生可继续。
   - `rejected`：前端提示，医生须换药。
5. 结束诊次（`POST /consults/{no}/finish`）→ 调 `platform_clearing` 按比例计费分账（个人/科室/机构/平台）。

## 数据模型（schema: scenario_teleconsult）
- `consult`：复诊会话（状态机 waiting → in_progress → finished）。
- `consult_rx`：电子处方（含 AI 审方结果 ai_review + review_note）。

## 依赖的平台能力
- 登录鉴权：platform-auth（网关注入身份，`require_cap("teleconsult:treat")`）
- AI 审方：`http://localhost:8103/api/platform-ai/rx-review`（不经网关，同容器 localhost）
  - platform-ai 不可达时自动降级本地 NSAID 规则引擎
- 计费分账：`platform_clearing.service_rate_card / income_event / income_split`
- 数据权限：py_common `scope_filter` 按 `dept_code` 隔离

## 对外暴露的接口（路径前缀 /api/scenario-006）
- `GET /consults` — 候诊/接诊队列（?status=waiting|in_progress|finished）
- `POST /consults/{no}/accept` — 接诊
- `POST /consults/{no}/prescribe` — 开方（AI 审方）
- `POST /consults/{no}/finish` — 结束 + 计费

## 合规要求
- AI 审方是辅助意见，最终决策权在医生（前端须展示该说明，`warn` 级别不强制拦截）。
- 只存 `patient_id` 引用，不自建患者表。
- 写操作必须落 audit_action；AI 调用不传患者 PII。

## 不要做的事
- ❌ 不要直接调 Claude API——走 `platform-ai` 服务，保持架构边界。
- ❌ 不要自存患者主数据。
- ❌ 硬编码计费金额——从 `service_rate_card` 动态读。
