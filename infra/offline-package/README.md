# 院内离线部署包

> ⚠️ 本目录是**院内私有化生产**部署方案（数据不出院）。与 Railway 演示用**同一个**单容器镜像。
> 生产 `.env` 必须 `SEED_DEMO=false`，只跑 schema 迁移，**绝不**灌演示患者数据。

## 架构：单容器镜像 + PostgreSQL
一个 `ai-hospital` 镜像内含：统一网关 + 全部平台服务/场景后端 + 聚合前端（portal + 各 Next 静态导出）。
配一个 PostgreSQL 即可运行。对外只暴露网关端口。

> 为什么不是多镜像微服务编排：单容器镜像已在演示环境充分验证，院内运维最简（导入 2 个镜像即可）。
> 如未来需拆分多镜像（按服务独立扩缩容），需为各 platform-* 服务补 Dockerfile 并改回多服务 compose。

## 文件
| 文件 | 作用 |
|---|---|
| `build-offline.sh <REGISTRY> <TAG>` | 构建机执行：构建镜像 + 导出离线包 `dist/ai-hospital-<TAG>.tar.gz` |
| `docker-compose.prod.yml` | 院内编排（app + postgres） |
| `install.sh` | 院内首次安装：导入镜像 → 起库 → 起 app（自动迁移） |
| `upgrade.sh <TAG>` | 升级：备份 → 导入新镜像 → 重启 app → 健康检查，失败自动回滚 |
| `backup.sh` / `restore.sh` | 数据库备份 / 恢复（升级前自动备份） |
| `healthcheck.sh` | 健康检查（`--wait-db` 等库就绪 / 默认查 app `/health`） |
| `.env.example` | 配置样例，复制为 `config/.env` 填写（**含密钥，不进仓库**） |

## 院内安装流程
```bash
tar -xzf ai-hospital-<TAG>.tar.gz && cd ai-hospital-<TAG>
cp config/.env.example config/.env && vi config/.env   # 填密钥，确认 SEED_DEMO=false
./install.sh
# 访问 http://<本机IP>:<PUBLIC_PORT>/health
```

## 升级 / 回滚
```bash
./upgrade.sh v1.1.0      # 先备份，迁移+健康检查失败自动回滚
./restore.sh --latest    # 手动恢复最近备份
```
