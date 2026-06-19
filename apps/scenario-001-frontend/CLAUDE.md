# CLAUDE.md · 场景 001 frontend · 在线随访

## 场景信息
- 编号：scenario-001
- 名称：在线随访
- 部分：前端 (Next.js)
- 负责人：owner-001
- 一句话：<它解决什么问题、给谁用>

## 核心业务流程
<用 3~6 步把主流程说清楚>

## 依赖的平台能力（必须复用，不要自建）
- 登录鉴权：platform-auth（经网关注入身份）
- 患者档案：platform-patient（HTTP，勿自存患者表）
- 文件/影像：platform-file　|　AI 能力：platform-ai
- 调后端统一用 @hospital/sdk；类型用 @hospital/shared-types；组件用 @hospital/ui

## 对外暴露的接口
- 路径前缀：/api/scenario-001
<列出主要 API>

## 领域术语 & 数据模型
<术语表 + 关键实体字段，标注敏感字段>

## 业务规则与边界
<特殊规则、状态机、权限规则、易错点>

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
