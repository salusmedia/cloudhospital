# CLAUDE.md · 统一网关 (gateway)

## 职责
所有外部请求的唯一入口。**鉴权 → 剥离伪造身份头 → 注入可信 X-User-* → 按前缀路由转发**到上游场景/平台服务。

## 关键文件
- `app/main.py`：主流程（catch-all 代理 + 鉴权门禁）。
- `app/routing.py`：路由表 = 平台内置路由 + `routes.json`(脚手架维护)；最长前缀匹配。
- `app/identity.py`：身份头处理（**安全关键**：先 strip 客户端 X-User-*，校验后再注入）。
- `app/proxy.py`：httpx 转发（单独成模块便于测试 monkeypatch）。

## 安全红线（改这里务必谨慎）
- 客户端的 `X-User-*` 和 `Authorization` **必须**在转发前剥离/不下传，严禁透传客户端伪造身份。
- 受保护路由无有效令牌一律 401；只有 `public=True` 路由（如登录）放行。
- `jwt_secret` 必须与 platform-auth 一致，由环境注入，**绝不写死/不进仓库/不进镜像**。

## 端口约定
- 平台服务 81xx（auth=8101, patient=8102, ai=8103, file=8104）。
- 场景后端 8000+编号（来自 routes.json）。
- 网关自身默认 8080。

## 配置（环境变量，前缀 GATEWAY_）
- `GATEWAY_JWT_SECRET`、`GATEWAY_ROUTES_FILE`、`GATEWAY_USE_LOCALHOST`(开发置 true)、`GATEWAY_REQUEST_TIMEOUT`。

## 测试
- `tests/test_routing.py`：路由/身份纯函数。
- `tests/test_gateway_flow.py`：鉴权链路（monkeypatch 转发）。
- 改动鉴权/路由/身份逻辑，必须补测越权、伪造头、过期令牌等用例。
