# CLAUDE.md · 统一门户 (apps/portal)

## 职责
聚合各编号场景入口的**统一医护工作站**（单页应用），由网关同源托管（`GATEWAY_WEB_ROOT`）。
登录后顶部标签切换：转诊一件事(019) / 在线复诊(006) / 家庭病床(002) / MDT / 管理 / 信用；
居民账号(resident)登录则进患者端移动视图。

## 与场景前端的边界
- portal 是**一体化综合工作站**（纯 HTML/JS，内联各场景 UI 模块），托管在 web 根 `/`。
- 各场景/角色已另有**独立 Next 应用**（同源、各自 basePath，见 `DEPLOY.md` 路径表）：
  `/patient`（居民端）、`/regulator`（监管端）、`/scenario-XXX`（各场景医护端）。
  portal 与这些独立应用**并存**：portal 给"一个账号看全部"的综合视图，独立应用给单端聚焦体验。
- 调接口统一经网关 `/api/*`（同源，免跨域）；鉴权用登录返回的访问令牌 + 刷新令牌。

## 文件
- `index.html` / `style.css` / `app.js`：单页门户（无构建步骤，被 Dockerfile 直接拷进 web 根 `/`）。
- 独立 Next 应用经 Dockerfile 的 web-builder 阶段静态导出后落各子目录（见 DEPLOY.md 镜像构建）。

## 不要做的事
- ❌ 不要在门户里写患者主数据/业务持久化——走平台服务与场景 API。
- ❌ 不要把敏感数据写进日志。
