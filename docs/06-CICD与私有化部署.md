# 06 · CI/CD 与私有化部署

> 私有化（院内本地部署）的核心矛盾：**院内网络隔离、不能联网拉镜像/装包**。
> 解法：在**外部 CI 一次构建好所有镜像 → 导出成离线安装包 → 拷进院内 → 一键安装/升级**。

---

## 1. 整体发布流水线

```
开发者合并到 main
      │
      ▼
[CI] 构建所有镜像 (前端/后端/网关/平台服务) ──► 推到内网镜像仓库 (Harbor)
      │                                              │
      ▼                                              ▼
自动部署 test 环境  ──►  人工验证  ──►  打 release tag (v1.4.0)
                                              │
                                              ▼
                              [CI] 拉取该 tag 全部镜像 → docker save 导出
                                   + compose 文件 + 数据库迁移 + 安装脚本
                                              │
                                              ▼
                                  生成离线安装包  ai-hospital-v1.4.0.tar.gz
                                              │
                          (U盘/堡垒机/审批通道 拷入院内)
                                              ▼
                          院内执行 ./install.sh 或 ./upgrade.sh
```

**铁律：进院内的镜像 = test/staging 验证过的同一镜像（同 digest），院内绝不重新构建。**

---

## 2. 镜像构建（CI 阶段）

- 每个服务一个 `Dockerfile`（在 `infra/docker/`）。
- 镜像 tag 用 **语义化版本 + git sha**：`harbor.内网/ai-hospital/scenario-001-backend:v1.4.0`。
- 前端 Next.js 用多阶段构建产出静态/standalone；后端用 slim Python 基础镜像 + 依赖锁定安装。
- 基础镜像统一从内网 Harbor 拉，不依赖公网。

`.gitlab-ci.yml` 关键阶段：`lint → test → build-images → deploy-test →（手动）release → package-offline`。

---

## 3. 离线安装包内容

```
ai-hospital-v1.4.0/
├── images/                      # 所有 docker save 导出的 .tar 镜像
│   ├── gateway.tar
│   ├── scenario-001-backend.tar
│   └── ...
├── compose/
│   └── docker-compose.prod.yml  # 生产编排（含 PG/Redis/MinIO/各服务）
├── config/
│   ├── .env.example             # 院内填写：域名、端口、密钥
│   └── nginx/                   # 反向代理/TLS 配置
├── migrations/                  # 数据库迁移脚本（Alembic）
├── install.sh                   # 首次安装
├── upgrade.sh                   # 升级（含备份+迁移+回滚）
├── backup.sh / restore.sh       # 数据备份/恢复
├── healthcheck.sh               # 部署后健康检查
├── CHANGELOG.md                 # 本版变更
└── 部署手册.md                   # 给院内运维的图文步骤
```

---

## 4. 院内首次安装

```bash
tar -xzf ai-hospital-v1.4.0.tar.gz && cd ai-hospital-v1.4.0
# 1) 导入镜像
for f in images/*.tar; do docker load -i "$f"; done
# 2) 配置
cp config/.env.example config/.env   # 填写域名/端口/数据库密码/密钥
# 3) 启动
./install.sh                          # 起依赖→跑迁移→起服务→健康检查
```

`install.sh` 做的事：校验 Docker/资源 → `docker load` → 起 PG/Redis/MinIO → 等就绪 → 跑 DB 迁移 → 起网关+平台服务+各场景 → `healthcheck.sh` 验证 → 打印访问地址。

---

## 5. 院内升级（最关键、最易出事）

```bash
./upgrade.sh v1.4.0
```

`upgrade.sh` 必须做的事（按顺序）：

1. **备份**：`backup.sh` 全量备份数据库 + 对象存储 + 当前 compose/env。
2. 记录当前版本（用于回滚）。
3. `docker load` 新镜像。
4. **数据库迁移**：跑 Alembic，迁移脚本必须**向后兼容、可重入**。
5. 滚动重启服务（网关最后切，减少中断）。
6. `healthcheck.sh` 验证；失败则**自动回滚**到上一版本镜像 + 恢复备份。

> 升级前在 staging 用**院内数据的脱敏副本**演练过同样的升级路径，才允许进生产。

---

## 6. 配置与密钥管理

- 院内密钥（数据库密码、JWT 密钥、加密密钥）**只存在院内 `.env` / 密钥管理**，绝不进仓库、不进镜像。
- 镜像里只放代码，配置全外部注入（12-Factor）。
- 不同院区/客户用不同 `.env`，镜像复用。

---

## 7. 监控、日志、审计（院内）

- 日志集中：各容器日志 → 院内 Loki/ELK（离线版）。
- 监控：Prometheus + Grafana（离线版），看各服务健康、资源、接口延迟。
- **审计日志独立留存**：所有患者数据访问、关键操作落审计库，满足等保/合规追溯，保留期按医院制度。
- 日志中**禁止出现患者敏感明文**（CI 合规扫描 + `py-common` 脱敏中间件双保险）。

---

## 8. 版本与回滚策略

- 语义化版本 `MAJOR.MINOR.PATCH`；release tag 对应一个离线包。
- 每个离线包自带回滚能力（保留上一版本镜像与备份）。
- 紧急修复走 `fix/*` → 合 main → 出 `PATCH` 版离线包，流程不变只是更快。

---

## 9. 规模变大后：从 Compose 迁 K8s

院内规模/高可用要求上来后，把 `docker-compose.prod.yml` 对应到 K8s（Helm chart 放 `infra/k8s/`），离线包改为镜像 tar + Helm values + `helm upgrade`。**编排换了，"外部构建→离线导入→院内部署"的主链路不变。**
