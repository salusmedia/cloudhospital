# 部署到 Railway（演示）

> ⚠️ **合规**：本平台为**私有化/院内部署**设计（数据不出院）。Railway 是公网云，**仅可用当前
> 模拟数据做演示/路演**，严禁放真实患者数据。生产上线仍走 `infra/offline-package` 离线部署。

## 架构（单容器 + Postgres）
一个镜像内跑：统一网关 + 全部平台服务(auth/patient/ai/file/archive/iot/consent) + 场景后端(001/002/006/019) + 聚合前端。
网关用 `GATEWAY_USE_LOCALHOST=true` 经 localhost 互联，对外只暴露网关（Railway 的 `$PORT`）。
→ Railway 上只有 **2 个服务**：本应用 + PostgreSQL 插件。

关键文件：`Dockerfile`、`scripts/start-container.sh`、`railway.json`、`.dockerignore`。

### 镜像构建：两阶段
1. **web-builder（Node 20）**：pnpm 编译 6 个独立 Next 应用为**静态导出**（`output:export`），
   按 `basePath` 装配进统一 web 根 `/web`（portal 静态站在根，各 app 落子目录）。
2. **运行镜像（Python 3.12）**：`uv sync` 装后端依赖；从 stage1 拷入 `/web`；Node 不进最终镜像。
   网关 `GATEWAY_WEB_ROOT=/app/web` 同源托管全部前端 + `/api/*` 反代后端。

> ⚠️ 加了 Node 编译阶段后**首次构建变慢**（多 2-4 分钟）。这是预期的。

### 前端托管：聚合 web 根 + basePath
| 路径 | 应用 | 源码 |
|---|---|---|
| `/` | 综合工作站（portal，静态 HTML） | `apps/portal` |
| `/patient` | 居民健康门户 | `apps/patient-portal` |
| `/regulator` | 医共体监管驾驶舱 | `apps/regulator-portal` |
| `/scenario-001` `/scenario-002` `/scenario-006` `/scenario-019` | 各场景医护端 | `apps/scenario-XXX-frontend` |

网关 `_serve_static`：目录→`index.html`；未命中文件→按首段路径回落到该 app 的 `index.html`（每 app 独立 SPA 兜底），都不命中才回 portal 根。

> 各 Next 应用经 `@hospital/sdk` 调 `/api/*`。SDK 直接返回后端裸载荷（**不**包 `{data}` 信封），
> 错误体读 FastAPI 的 `detail`/网关的 `message`。共享组件用 `@hospital/ui`（需 `transpilePackages`）。

---

## 第一步：推到 GitHub
```bash
cd D:\claude-coding\ai-cloud-hospital
git init -b main
git add .
git commit -m "chore: AI 云医院平台（演示版，含单容器部署）"
# 在 GitHub 网页建一个【私有】仓库（建议私有），拿到地址，然后：
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git push -u origin main
```
> 已配 `.gitignore`：不会提交 `.venv/node_modules/.env/*.key`。提交前可 `git status` 核对。

## 第二步：Railway 部署
1. 登录 https://railway.app → **New Project** → **Deploy from GitHub repo** → 选刚推的仓库。
   Railway 会读 `railway.json` 用 Dockerfile 构建（首次构建约 3-6 分钟）。
2. 在同一 Project 里 **New** → **Database** → **Add PostgreSQL**。Railway 会给该库注入 `DATABASE_URL`。
3. 让应用拿到数据库连接串：进应用服务 → **Variables** → **Add Reference** → 选 Postgres 的 `DATABASE_URL`
   （即把 `${{Postgres.DATABASE_URL}}` 绑到应用的 `DATABASE_URL`）。
4. 再加两个变量（演示可随意填，但别用默认值）：
   - `JWT_SECRET` = 任意长随机串（网关与 auth 共享）
   - `PII_KEY` = 任意长随机串（患者字段加密密钥）
5. 应用服务 → **Settings** → **Networking** → **Generate Domain**，得到公网地址。
6. 等部署完成（启动时自动跑 `alembic upgrade` 建表 + 灌种子）。

## 第三步：验证
健康检查：`https://<域名>/health` 应返回 `{"status":"ok","service":"gateway",...}`。

三端入口（均同源，登录态各自存 localStorage）：
| 端 | 路径 | 演示账号 |
|---|---|---|
| 综合工作站（portal） | `/` | doctor_card / 123456 |
| 居民健康门户 | `/patient` | patient_zjg / 123456 |
| 医共体监管驾驶舱 | `/regulator` | admin / admin123 |
| 转诊一件事（医护） | `/scenario-019` | doctor_card / 123456 |
| 在线复诊（医护） | `/scenario-006` | doctor_card / 123456 |
| 家庭病床（医护） | `/scenario-002` | doctor_card / 123456 |

验证独立应用是否真正生效（而非回落 portal）：`curl /regulator` 应含 `/regulator/_next/` 资源引用；
其静态 chunk（`/regulator/_next/static/chunks/*.js`）应返回 200。

---

## 环境变量清单
| 变量 | 来源/说明 |
|---|---|
| `DATABASE_URL` | **Railway Postgres 注入**（引用 `${{Postgres.DATABASE_URL}}`）。启动脚本自动转 `+psycopg` 方言。 |
| `JWT_SECRET` | 你设。网关/auth 共享的令牌密钥。 |
| `PII_KEY` | 你设。患者敏感字段加密密钥（与种子一致即可解密演示数据）。 |
| `PORT` | Railway 自动注入，网关绑定它。 |

## 常见问题
- **healthcheck 超时**：容器内要起 10 个进程 + 迁移 + 种子，首启较慢。`railway.json` 已设 300s；
  仍超时可在 Settings 调大，或把种子改成一次性 job。
- **内存**：~10 个 uvicorn 进程约需 ≥512MB。用 Railway Hobby（$5）即可，Free 额度可能偏紧。
- **构建失败 `uv sync`**：确认仓库根有各 service 的 `pyproject.toml`（workspace 成员）。
- **每次重启数据被重置**：启动脚本会重跑幂等种子，演示数据会回到初始态——这是有意为之；
  不想每次灌种子，把 `start-container.sh` 里的 seed 行去掉。
- **`/patient`、`/regulator`、`/scenario-XXX` 打开却是 portal 工作站**：说明该 Next 应用没被构建进
  `/web`，网关回落到了 portal 根 `index.html`。查 Dockerfile 的 web-builder 阶段构建/装配是否成功，
  以及 `start-container.sh` 的 `GATEWAY_WEB_ROOT` 是否指向 `/app/web`。
- **前端构建失败 `pnpm install`/`next build`**：Node 阶段用 `--frozen-lockfile`，改了前端依赖要先本地
  `pnpm install` 更新并提交 `pnpm-lock.yaml`；Card 等共享组件改动在 `packages/ui`。
- **前端能打开但取不到数据**：检查 `@hospital/sdk` 是否原样返回后端裸载荷（后端**不**包 `{data}` 信封）。
- **真实上线**：不要用本方案。走 `docs/06-CICD与私有化部署.md` 的离线镜像 + 院内部署。
