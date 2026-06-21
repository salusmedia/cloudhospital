# CLAUDE.md · platform-ai

## 职责
平台 AI 能力服务：为各场景提供通用 AI 推理能力，当前包括：
- **处方审方**（rx-review）：检查药品合理性，分级输出 passed / warn / rejected。
- **AI 分诊**（triage）：根据主诉给出 P1/P2/P3 就诊优先级。

## 端口
`8103`（单容器内 localhost:8103；平台服务 81xx 约定）

## AI 引擎选择
- 配置 `ANTHROPIC_API_KEY`（或 `PLATFORM_AI_ANTHROPIC_API_KEY`）→ 调 Claude API（默认模型 claude-haiku-4-5-20251001）。
- 未配置 → 自动降级到规则引擎（NSAID 相互作用 + 青霉素过敏检测 + 关键词分诊）。
- `PLATFORM_AI_ANTHROPIC_MODEL` 可覆盖模型名。

## 接口
- `POST /api/platform-ai/rx-review` — 处方审方（需鉴权）
- `POST /api/platform-ai/triage` — AI 分诊（需鉴权）
- `GET /health` — 健康探针

## 调用方式
- 场景后端（如 scenario-006）经 localhost:8103 直接调（容器内）；不经网关。
- 转发 `X-User-*` 头以保持身份链路 + 落审计日志。

## 无数据库依赖
platform-ai 是无状态服务，不连数据库，重启即恢复。

## 合规
- 调用 Claude API 时**不得**在 prompt 中包含患者姓名、身份证、手机号等 PII。
- 处方中的药品名、用法用量属于医疗信息，可发送；患者诊断摘要须脱敏后传入。
