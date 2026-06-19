# 部署到 Railway（演示）

> ⚠️ **合规**：本平台为**私有化/院内部署**设计（数据不出院）。Railway 是公网云，**仅可用当前
> 模拟数据做演示/路演**，严禁放真实患者数据。生产上线仍走 `infra/offline-package` 离线部署。

## 架构（单容器 + Postgres）
一个镜像内跑：统一网关 + 全部平台服务(auth/patient/archive/iot/consent/file) + 场景后端(002/006/019/001) + 静态门户。
网关用 `GATEWAY_USE_LOCALHOST=true` 经 localhost 互联，对外只暴露网关（Railway 的 `$PORT`）。
→ Railway 上只有 **2 个服务**：本应用 + PostgreSQL 插件。

关键文件：`Dockerfile`、`scripts/start-container.sh`、`railway.json`、`.dockerignore`。

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
浏览器打开生成的域名：
- 看到登录页 → 用 **doctor_card / 123456** 登录（身份来自数据库）
- 顶部切「转诊一件事 / 在线复诊 / 家庭病床 / 管理 / 信用」逐个点
- 患者端：用 **patient_zjg / 123456** 登录

健康检查：`https://<域名>/health` 应返回 `{"status":"ok","service":"gateway",...}`。

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
- **真实上线**：不要用本方案。走 `docs/06-CICD与私有化部署.md` 的离线镜像 + 院内部署。
