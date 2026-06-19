#!/usr/bin/env node
// new-scenario.mjs —— AI 云医院新场景脚手架
//
// 生成一个编号场景的完整可运行骨架，并自动接线：
//   - apps/scenario-XXX-frontend/    (Next.js 子应用 + CLAUDE.md + 示例页 + 测试)
//   - services/scenario-XXX-backend/ (FastAPI 服务 + CLAUDE.md + 示例接口 + 测试)
//   - services/gateway/routes.json   (注册路由，自动分配端口 8000+编号)
//   - docs/场景登记表.md              (追加登记行)
//   - .gitlab/CODEOWNERS             (追加负责人评审规则)
//
// 用法：
//   交互式:   node scripts/new-scenario.mjs
//   非交互:   node scripts/new-scenario.mjs --id 005 --name 在线随访 --owner zhangsan
//   选项:     --no-frontend   不生成前端
//             --no-backend    不生成后端
//             --force         覆盖已存在目录（危险，慎用）
//
// 零外部依赖，仅用 Node 内置模块。Windows / macOS / Linux 通用。

import { readFileSync, writeFileSync, existsSync, mkdirSync, rmSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createInterface } from "node:readline/promises";
import { stdin, stdout } from "node:process";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");

// ---------------------------------------------------------------- 工具函数

function parseArgs(argv) {
  const args = { flags: new Set(), opts: {} };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--no-frontend") args.flags.add("noFrontend");
    else if (a === "--no-backend") args.flags.add("noBackend");
    else if (a === "--force") args.flags.add("force");
    else if (a.startsWith("--")) args.opts[a.slice(2)] = argv[++i];
  }
  return args;
}

function fail(msg) {
  console.error(`\n❌ ${msg}\n`);
  process.exit(1);
}

// 写文件（自动建父目录）。已存在则按 force 决定是否覆盖。
function write(relPath, content, { force }) {
  const full = join(ROOT, relPath);
  if (existsSync(full) && !force) fail(`文件已存在: ${relPath}（用 --force 覆盖）`);
  mkdirSync(dirname(full), { recursive: true });
  writeFileSync(full, content.replace(/\r?\n/g, "\n"), "utf8");
  console.log(`  ✓ ${relPath}`);
}

// 幂等地往文件追加一段（若标记已存在则跳过）。
function appendOnce(relPath, marker, block) {
  const full = join(ROOT, relPath);
  if (!existsSync(full)) {
    console.log(`  ! 跳过追加（文件不存在）: ${relPath}`);
    return;
  }
  const cur = readFileSync(full, "utf8");
  if (cur.includes(marker)) {
    console.log(`  · 已登记，跳过: ${relPath}`);
    return;
  }
  writeFileSync(full, cur.replace(/\s*$/, "") + "\n" + block + "\n", "utf8");
  console.log(`  ✓ 更新 ${relPath}`);
}

function fillTemplate(str, vars) {
  return str.replace(/\{\{(\w+)\}\}/g, (_, k) => (k in vars ? vars[k] : `{{${k}}}`));
}

// 把一行插入 Markdown 表格内（在最后一条表格行之后），而不是追加到文件末尾。
// marker 用于幂等：已存在则跳过。
function insertTableRow(relPath, marker, row) {
  const full = join(ROOT, relPath);
  if (!existsSync(full)) {
    console.log(`  ! 跳过登记（文件不存在）: ${relPath}`);
    return;
  }
  const lines = readFileSync(full, "utf8").split(/\r?\n/);
  if (lines.some((l) => l.includes(marker))) {
    console.log(`  · 已登记，跳过: ${relPath}`);
    return;
  }
  const sep = lines.findIndex((l) => /^\|[\s-]*-{2,}/.test(l)); // 表头分隔行 |----|
  if (sep === -1) fail(`${relPath} 未找到表格分隔行，无法自动登记。`);
  let last = sep;
  for (let i = sep + 1; i < lines.length && lines[i].trimStart().startsWith("|"); i++) last = i;
  lines.splice(last + 1, 0, row);
  writeFileSync(full, lines.join("\n"), "utf8");
  console.log(`  ✓ 登记到 ${relPath}`);
}

// ---------------------------------------------------------------- 校验

function validateId(id) {
  if (!/^\d{3}$/.test(id)) fail(`编号必须是三位数字（如 005），收到: "${id}"`);
}

function ensureNotExists(id, force) {
  const fe = join(ROOT, `apps/scenario-${id}-frontend`);
  const be = join(ROOT, `services/scenario-${id}-backend`);
  if (!force && (existsSync(fe) || existsSync(be))) {
    fail(`场景 ${id} 目录已存在。换个编号，或加 --force 覆盖。`);
  }
  if (force) {
    for (const d of [fe, be]) if (existsSync(d)) rmSync(d, { recursive: true, force: true });
  }
}

// ---------------------------------------------------------------- 交互

async function prompt(opts) {
  // 已有命令行参数则不进入交互
  if (opts.id) return opts;
  const rl = createInterface({ input: stdin, output: stdout });
  const ask = async (q, def) => {
    const a = (await rl.question(def ? `${q} [${def}]: ` : `${q}: `)).trim();
    return a || def || "";
  };
  const res = {};
  res.id = await ask("场景编号(三位数字)", "");
  res.name = await ask("场景中文名", "");
  res.owner = await ask("负责人(GitLab 用户名)", "");
  const fe = (await ask("生成前端? (y/n)", "y")).toLowerCase();
  const be = (await ask("生成后端? (y/n)", "y")).toLowerCase();
  await rl.close();
  return { ...res, noFrontend: fe === "n", noBackend: be === "n" };
}

// ================================================================ 模板

const T = {
  // ---------------- 前端 ----------------
  fePackageJson: `{
  "name": "@hospital/scenario-{{ID}}-frontend",
  "private": true,
  "version": "0.1.0",
  "scripts": {
    "dev": "next dev --port {{FE_PORT}}",
    "build": "next build",
    "lint": "eslint .",
    "typecheck": "tsc --noEmit",
    "test": "vitest run"
  },
  "dependencies": {
    "next": "^14.2.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "@hospital/sdk": "workspace:*",
    "@hospital/ui": "workspace:*",
    "@hospital/shared-types": "workspace:*"
  },
  "devDependencies": {
    "@hospital/config": "workspace:*",
    "@types/react": "^18.3.0",
    "typescript": "^5.5.0",
    "vitest": "^2.0.0"
  }
}
`,

  feTsconfig: `{
  "extends": "@hospital/config/tsconfig.base.json",
  "compilerOptions": {
    "plugins": [{ "name": "next" }],
    "jsx": "preserve"
  },
  "include": ["src", "next-env.d.ts"],
  "exclude": ["node_modules", ".next"]
}
`,

  feNextConfig: `/** @type {import('next').NextConfig} */
// 每个场景前端挂载在 /scenario-{{ID}} 路径下，由门户/网关聚合。
const nextConfig = {
  basePath: "/scenario-{{ID}}",
  output: "standalone",
};
export default nextConfig;
`,

  feLayout: `export const metadata = { title: "场景{{ID}} · {{NAME}}" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
`,

  fePage: `import { greeting } from "./lib";

// 示例页面：替换成本场景的真实 UI。调后端请用 @hospital/sdk。
export default function Page() {
  return (
    <main style={{ padding: 24 }}>
      <h1>场景 {{ID}} · {{NAME}}</h1>
      <p>{greeting("{{NAME}}")}</p>
      <p>这是脚手架生成的示例页，删除后开始你的开发。</p>
    </main>
  );
}
`,

  feLib: `// 一个纯函数示例，便于演示无需 DOM 的单元测试。
export function greeting(name: string): string {
  return \`欢迎使用 \${name}\`;
}
`,

  feTest: `import { describe, it, expect } from "vitest";
import { greeting } from "./lib";

describe("scenario-{{ID}} frontend", () => {
  it("greeting 拼接名称", () => {
    expect(greeting("随访")).toBe("欢迎使用 随访");
  });
});
`,

  feEnvDts: `/// <reference types="next" />\n/// <reference types="next/image-types/global" />\n`,

  feDockerfile: `# 场景 {{ID}} 前端镜像（Next.js standalone）。由 CI 构建，离线包导入院内。
FROM node:20-alpine AS deps
WORKDIR /app
RUN corepack enable
COPY . .
RUN pnpm install --frozen-lockfile --filter @hospital/scenario-{{ID}}-frontend...

FROM deps AS build
RUN pnpm --filter @hospital/scenario-{{ID}}-frontend build

FROM node:20-alpine AS run
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/apps/scenario-{{ID}}-frontend/.next/standalone ./
COPY --from=build /app/apps/scenario-{{ID}}-frontend/.next/static ./apps/scenario-{{ID}}-frontend/.next/static
EXPOSE {{FE_PORT}}
CMD ["node", "apps/scenario-{{ID}}-frontend/server.js"]
`,

  // ---------------- 后端 ----------------
  bePyproject: `[project]
name = "scenario-{{ID}}-backend"
version = "0.1.0"
description = "{{NAME}} —— 场景 {{ID}} 后端"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.30",
  "pydantic-settings>=2.4",
  "py-common",   # 共享库：鉴权/审计/脱敏/日志/DB（uv workspace 内解析）
]

[tool.uv.sources]
py-common = { workspace = true }

[dependency-groups]
dev = ["pytest>=8.3", "httpx>=0.27", "mypy>=1.11", "ruff>=0.6"]

[tool.ruff]
line-length = 100

[tool.pytest.ini_options]
testpaths = ["tests"]
`,

  beConfig: `from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SCENARIO_{{ID}}_")

    scenario_id: str = "{{ID}}"
    api_prefix: str = "/api/scenario-{{ID}}"
    # 数据库/密钥等通过环境注入，绝不写死（见根 CLAUDE.md 合规条款）。
    database_url: str = "postgresql://dev:dev@localhost:5432/hospital"


settings = Settings()
`,

  beRoutes: `from fastapi import APIRouter

from app.core.config import settings

# 本场景对外接口。路径前缀已含 /api/scenario-{{ID}}，由网关统一路由。
router = APIRouter(prefix=settings.api_prefix, tags=["scenario-{{ID}}"])


@router.get("/ping")
async def ping() -> dict[str, str]:
    """示例接口：替换成本场景真实业务。

    提示：
    - 鉴权、审计、脱敏请用 packages/py-common 的中间件。
    - 患者数据走 platform-patient，不要在本服务自建患者表。
    """
    return {"scenario": settings.scenario_id, "message": "pong"}
`,

  beMain: `from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(title="场景{{ID}} · {{NAME}}")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "scenario": "{{ID}}"}


app.include_router(router)
`,

  beInit: `# 场景 {{ID}} 后端包\n`,

  beTest: `from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["scenario"] == "{{ID}}"


def test_ping():
    r = client.get("/api/scenario-{{ID}}/ping")
    assert r.status_code == 200
    assert r.json()["message"] == "pong"
`,

  beDockerfile: `# 场景 {{ID}} 后端镜像。由 CI 构建，离线包导入院内。
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY services/scenario-{{ID}}-backend/pyproject.toml ./
RUN uv pip install --system --no-cache .
COPY services/scenario-{{ID}}-backend/app ./app
EXPOSE {{BE_PORT}}
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "{{BE_PORT}}"]
`,

  // ---------------- 通用 ----------------
  scenarioReadme: `# 场景 {{ID}} · {{NAME}}

- 负责人：{{OWNER}}
- 前端：\`apps/scenario-{{ID}}-frontend\`（端口 {{FE_PORT}}）
- 后端：\`services/scenario-{{ID}}-backend\`（端口 {{BE_PORT}}，前缀 \`/api/scenario-{{ID}}\`）

## 本地起这个场景
\`\`\`bash
pnpm run dev --filter=scenario-{{ID}}-*
# 后端单独起：cd services/scenario-{{ID}}-backend && uv run uvicorn app.main:app --reload --port {{BE_PORT}}
\`\`\`

开发规范见本目录 \`CLAUDE.md\` 与仓库 \`docs/04-应用场景开发流程.md\`。
`,
};

// 场景级 CLAUDE.md（基于 docs/templates/scenario-CLAUDE.md，已填入编号）
function scenarioClaudeMd(kind, v) {
  return `# CLAUDE.md · 场景 ${v.ID} ${kind} · ${v.NAME}

## 场景信息
- 编号：scenario-${v.ID}
- 名称：${v.NAME}
- 部分：${kind === "frontend" ? "前端 (Next.js)" : "后端 (FastAPI)"}
- 负责人：${v.OWNER || "<填写>"}
- 一句话：<它解决什么问题、给谁用>

## 核心业务流程
<用 3~6 步把主流程说清楚>

## 依赖的平台能力（必须复用，不要自建）
- 登录鉴权：platform-auth（经网关注入身份）
- 患者档案：platform-patient（HTTP，勿自存患者表）
- 文件/影像：platform-file　|　AI 能力：platform-ai
${
  kind === "frontend"
    ? "- 调后端统一用 @hospital/sdk；类型用 @hospital/shared-types；组件用 @hospital/ui"
    : "- 鉴权/日志/审计/脱敏/DB 基类统一用 packages/py-common"
}

## 对外暴露的接口
- 路径前缀：/api/scenario-${v.ID}
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
- 提交前：pnpm run check --filter=scenario-${v.ID}-*

## 不要做的事
- ❌ 不要直接 import 其他 scenario-* 的代码（走共享层或 HTTP）。
- ❌ 不要自存患者/用户主数据。
- ❌ 不要把敏感数据写进日志或提交记录。
${kind === "backend" ? "- ❌ 改接口后记得让前端 pnpm run gen:types 同步类型。" : "- ❌ 后端接口变更后记得 pnpm run gen:types 再用新类型。"}
`;
}

// ---------------------------------------------------------------- 接线

// 注册到网关路由表 services/gateway/routes.json（不存在则创建）
function registerGatewayRoute(v) {
  const rel = "services/gateway/routes.json";
  const full = join(ROOT, rel);
  let data = { routes: [] };
  if (existsSync(full)) {
    try {
      data = JSON.parse(readFileSync(full, "utf8"));
    } catch {
      fail(`${rel} 不是合法 JSON，无法自动注册路由，请手工处理。`);
    }
  }
  if (!Array.isArray(data.routes)) data.routes = [];
  if (data.routes.some((r) => r.scenario === v.ID)) {
    console.log(`  · 网关已注册场景 ${v.ID}，跳过`);
    return;
  }
  data.routes.push({
    scenario: v.ID,
    prefix: `/api/scenario-${v.ID}`,
    service: `scenario-${v.ID}-backend`,
    port: Number(v.BE_PORT),
  });
  data.routes.sort((a, b) => a.scenario.localeCompare(b.scenario));
  mkdirSync(dirname(full), { recursive: true });
  writeFileSync(full, JSON.stringify(data, null, 2) + "\n", "utf8");
  console.log(`  ✓ 更新 ${rel}（注册 /api/scenario-${v.ID} → 端口 ${v.BE_PORT}）`);
}

// ---------------------------------------------------------------- 主流程

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const answers = await prompt({
    id: args.opts.id,
    name: args.opts.name,
    owner: args.opts.owner,
  });

  const id = (args.opts.id || answers.id || "").trim();
  const name = (args.opts.name || answers.name || "").trim() || `场景${id}`;
  const owner = (args.opts.owner || answers.owner || "").trim();
  const noFrontend = args.flags.has("noFrontend") || answers.noFrontend;
  const noBackend = args.flags.has("noBackend") || answers.noBackend;
  const force = args.flags.has("force");

  validateId(id);
  if (noFrontend && noBackend) fail("前端和后端不能同时不生成。");
  ensureNotExists(id, force);

  const v = {
    ID: id,
    ID_US: id, // 下划线版（编号已是数字，保持一致）
    NAME: name,
    OWNER: owner,
    FE_PORT: String(3000 + Number(id)), // 3001, 3002...
    BE_PORT: String(8000 + Number(id)), // 8001, 8002...
  };

  console.log(`\n🚀 生成场景 ${id} · ${name}${owner ? ` (负责人 ${owner})` : ""}\n`);

  // ---- 前端 ----
  if (!noFrontend) {
    console.log("前端 apps/scenario-" + id + "-frontend:");
    const base = `apps/scenario-${id}-frontend`;
    write(`${base}/package.json`, fillTemplate(T.fePackageJson, v), { force });
    write(`${base}/tsconfig.json`, fillTemplate(T.feTsconfig, v), { force });
    write(`${base}/next.config.mjs`, fillTemplate(T.feNextConfig, v), { force });
    write(`${base}/next-env.d.ts`, fillTemplate(T.feEnvDts, v), { force });
    write(`${base}/Dockerfile`, fillTemplate(T.feDockerfile, v), { force });
    write(`${base}/README.md`, fillTemplate(T.scenarioReadme, v), { force });
    write(`${base}/CLAUDE.md`, scenarioClaudeMd("frontend", v), { force });
    write(`${base}/src/app/layout.tsx`, fillTemplate(T.feLayout, v), { force });
    write(`${base}/src/app/page.tsx`, fillTemplate(T.fePage, v), { force });
    write(`${base}/src/app/lib.ts`, fillTemplate(T.feLib, v), { force });
    write(`${base}/src/app/lib.test.ts`, fillTemplate(T.feTest, v), { force });
  }

  // ---- 后端 ----
  if (!noBackend) {
    console.log("后端 services/scenario-" + id + "-backend:");
    const base = `services/scenario-${id}-backend`;
    write(`${base}/pyproject.toml`, fillTemplate(T.bePyproject, v), { force });
    write(`${base}/README.md`, fillTemplate(T.scenarioReadme, v), { force });
    write(`${base}/CLAUDE.md`, scenarioClaudeMd("backend", v), { force });
    write(`${base}/Dockerfile`, fillTemplate(T.beDockerfile, v), { force });
    write(`${base}/app/__init__.py`, fillTemplate(T.beInit, v), { force });
    write(`${base}/app/main.py`, fillTemplate(T.beMain, v), { force });
    write(`${base}/app/core/__init__.py`, "", { force });
    write(`${base}/app/core/config.py`, fillTemplate(T.beConfig, v), { force });
    write(`${base}/app/api/__init__.py`, "", { force });
    write(`${base}/app/api/routes.py`, fillTemplate(T.beRoutes, v), { force });
    write(`${base}/tests/__init__.py`, "", { force });
    write(`${base}/tests/test_health.py`, fillTemplate(T.beTest, v), { force });
  }

  // ---- 接线 ----
  console.log("接线:");
  if (!noBackend) registerGatewayRoute(v);

  insertTableRow(
    "docs/场景登记表.md",
    `/api/scenario-${id} `,
    `| ${id} | ${name} | ${owner || "<填写>"} | auth, patient | /api/scenario-${id} | 开发中 | 脚手架生成 |`
  );

  appendOnce(
    ".gitlab/CODEOWNERS",
    `scenario-${id}-`,
    `${!noFrontend ? `/apps/scenario-${id}-frontend/        @${owner || "owner-" + id}\n` : ""}` +
      `${!noBackend ? `/services/scenario-${id}-backend/     @${owner || "owner-" + id}` : ""}`
  );

  // ---- 完成提示 ----
  console.log(`
✅ 场景 ${id} 生成完成。

下一步:
  1) 安装依赖:   pnpm install ${!noBackend ? "&& pnpm run setup:py" : ""}
  2) 本地启动:   pnpm run dev --filter=scenario-${id}-*
  3) 跑门禁:     pnpm run check --filter=scenario-${id}-*
  4) 完善规范:   编辑 ${!noFrontend ? `apps/scenario-${id}-frontend/CLAUDE.md` : ""}${!noFrontend && !noBackend ? " 和 " : ""}${!noBackend ? `services/scenario-${id}-backend/CLAUDE.md` : ""}
  5) 切分支提交: git switch -c feature/scenario-${id}-初始化

注意: CODEOWNERS 里若用了占位 @owner-${id}，请改成真实 GitLab 用户/组。
`);
}

main().catch((e) => fail(e?.stack || String(e)));
