# CLAUDE.md · 平台服务 · 统一登录鉴权 (platform-auth)

## 职责
统一身份与令牌中心。校验账号 → 签发令牌（含 sub/name/roles/scopes）。
**令牌由 py_common.tokens 签发，gateway 用同一 secret 校验。**

## 关键约定
- `scopes` 用科室代码（ASCII，如 card/endo），与各场景的数据权限判定一致。
- `jwt_secret` 与 gateway 共享，环境注入，**绝不写死/不进仓库/不进镜像**（当前默认值仅本地开发用）。
- 登录路径 `/api/platform-auth/login` 在网关侧标记 public（免令牌）。

## 待办（生产化）
- `app/users.py` 现为演示账号 + sha256；生产对接 HIS/LDAP，密码用 bcrypt/argon2 + 盐。
- 增加令牌刷新、登出/吊销（黑名单或短 TTL + refresh）。
- `/me`、改密、登录审计等。

## 测试
- `tests/test_auth.py`：登录成功签发可校验令牌、密码错误/未知用户 401。
- 改鉴权逻辑必须补测。
