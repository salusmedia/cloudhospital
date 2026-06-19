# 01 · 环境搭建与 Claude Code 入门

> 目标：一个**从没用过 Claude Code 的新成员**，照着本文 30~60 分钟内完成：
> 装好环境 → 装好 Claude Code → 跑通本地项目 → 用 Claude Code 改一行代码并提交一个 MR。

---

## 第一部分：装开发环境

### 1.1 必装软件

| 软件 | 版本 | 说明 |
|------|------|------|
| Git | ≥ 2.40 | 代码版本管理 |
| Node.js | ≥ 20 LTS | 前端运行时 |
| pnpm | ≥ 9 | JS 包管理（`npm i -g pnpm`） |
| Python | 3.11 或 3.12 | 后端运行时 |
| uv | 最新 | Python 包/环境管理（`pip install uv`） |
| Docker Desktop | 最新 | 本地起数据库、最终容器化 |
| VS Code | 最新 | 推荐编辑器 |

> Windows 用户：建议在 **WSL2 + Ubuntu** 里开发，避免路径、换行符、脚本兼容问题。Docker Desktop 开启 WSL2 集成。

### 1.2 拉代码

```bash
git clone https://gitlab.内网地址/ai-cloud-hospital/platform.git
cd platform
```

### 1.3 安装依赖 & 起服务

```bash
pnpm install            # JS 全部依赖
pnpm run setup:py       # 各 Python 服务建虚拟环境 + 装依赖
docker compose -f infra/docker/compose.dev.yml up -d   # 起 PG/Redis/MinIO
pnpm run dev            # 起网关 + 所有场景（或 --filter 只起一个）
```

打开 `http://localhost:3000`，能看到平台首页即成功。

---

## 第二部分：装 Claude Code（新手重点）

### 2.1 什么是 Claude Code

Claude Code 是命令行里的 AI 编程助手。你用自然语言告诉它要做什么，它能**读代码、改代码、跑命令、跑测试**。在本项目里，它会自动读取每个目录的 `CLAUDE.md`，按我们团队的规范来写代码。

### 2.2 安装与登录

```bash
npm install -g @anthropic-ai/claude-code   # 安装
cd platform                                 # 进项目根目录
claude                                       # 启动，首次会引导登录
```

> 账号/额度由团队统一发放，找负责人要。**不要把 API Key 写进代码或提交到仓库。**

### 2.3 团队共享配置已经帮你配好了

进入仓库后，这些是**已经在仓库里、对所有人生效**的，你不用自己配：

- 每个目录的 `CLAUDE.md`：模块规范，Claude 会自动遵守。
- `.claude/settings.json`：团队共享的权限、钩子（比如提交前自动 lint）。
- `.claude/agents/`、`.claude/skills/`：团队共享的子代理和技能（见 [07](07-ClaudeCode进阶-子代理与技能.md)）。

> 个人偏好放 `.claude/settings.local.json`（已被 `.gitignore`，不会提交）。

### 2.4 新手必会的 5 个用法

| 你想做的事 | 怎么跟 Claude 说 |
|-----------|------------------|
| 看懂一段代码 | "解释 services/scenario-001-backend 的鉴权流程" |
| 加个功能 | "在场景 001 后端加一个按日期查询随访记录的接口，遵循本目录 CLAUDE.md" |
| 改 Bug | "场景 001 列表分页第二页重复，帮我定位并修复" |
| 写测试 | "为刚才改的接口补单元测试，覆盖空结果和越权两种情况" |
| 提交代码 | "帮我按团队提交规范生成 commit message"（**但 push/合并由你自己确认**） |

**新手三条铁律**：

1. **小步快跑**：一次让它做一件事，做完看 diff，再继续。不要"帮我把整个场景写完"。
2. **永远 review diff**：AI 写的代码你要看懂、要负责。看不懂就让它解释。
3. **跑测试再提交**：让它跑 `pnpm test` / `pytest`，绿了再说。

### 2.5 不要做的事

- ❌ 不要让 Claude 直接 `git push`、合并 MR、删分支——这些**人来确认**。
- ❌ 不要把真实患者数据贴进对话或测试。
- ❌ 不要绕过 `CLAUDE.md` 里的合规要求。

---

## 第三部分：你的第一个 MR（走一遍流程）

```bash
# 1) 从最新 main 切分支
git switch main && git pull
git switch -c feature/scenario-001-add-followup-query

# 2) 用 Claude Code 改代码（在项目根目录运行 claude）
#    例如让它加一个接口 + 测试，期间多次 review diff

# 3) 本地门禁
pnpm run check        # lint + typecheck + 测试（前后端都跑）

# 4) 提交（信息遵循 03 规范）
git add -p
git commit -m "feat(scenario-001): 新增按日期查询随访记录接口"

# 5) 推送并提 MR
git push -u origin feature/scenario-001-add-followup-query
# 到 GitLab 网页提 Merge Request，指派给场景负责人
```

合并规则、评审标准见 [05 代码评审与质量门禁](05-代码评审与质量门禁.md)。

---

## 常见问题

- **pnpm install 卡住** → 配置内网 npm 镜像（`.npmrc` 已指向内网 registry）。
- **Python 依赖装不上** → 用内网 PyPI 镜像，`uv` 已在 `pyproject.toml` 配好 index。
- **Docker 起不来** → 确认 Docker Desktop 已开 WSL2 集成；端口 5432/6379/9000 没被占用。
- **Claude 不按规范** → 检查你是不是在子目录启动的；在**项目根**启动它能读到全部 `CLAUDE.md`。
