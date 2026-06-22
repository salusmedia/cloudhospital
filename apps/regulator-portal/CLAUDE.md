# CLAUDE.md · 监管端 · 医共体监管驾驶舱 (apps/regulator-portal)

## 职责
医共体运营管理 / 监管者视角的全域聚合驾驶舱（深色指挥中心风格），basePath `/regulator`。
消费 scenario-019 的 admin API（全局聚合，不经 scope_filter）。

## 四个监管视图
1. **转诊监管看板**（`/scenario-019/admin/dashboard`）：转诊总量/接收率/检验互认率/急诊直转 KPI + 类型分布柱状 + 接收机构 TOP5 排行。
2. **绩效分账**（`/scenario-019/admin/settlements`）：协同服务计量（首诊识别/上转协同/下转康复）+ 机构分账明细表。
3. **规则配置**（`/scenario-019/admin/rules`）：病情分层标准 + 时限控制 + 检查检验互认目录。
4. **异常预警**（`/scenario-019/admin/alerts` + `/handle`）：分级预警列表 + 一键处置留痕。

## 文件
- `page.tsx`：单页四标签 SPA，含内置登录（admin/admin123）。
- `regulator-api.ts`：admin API 客户端封装。

## 权限说明
- 后端 admin 接口为全局聚合视图，生产应限定 `regulator`/`org_admin` 角色（演示期仅校验登录）。
- 监管账号：admin / admin123（admin 角色）。

## 依赖的平台能力
- 登录鉴权：platform-auth（token 存 localStorage）
- 调接口统一用 @hospital/sdk

## 不要做的事
- ❌ 不要在监管端做患者个体敏感数据展示——聚合统计为主，按需脱敏。
- ❌ 不要绕过 scenario-019-backend 直接查 DB。
