# infra/db · 平台数据库迁移

平台库的 DDL 与 Alembic 迁移。设计基准见 [docs/08-平台数据库设计](../../docs/08-数据库设计.md)。

## 目录

```
infra/db/
├── alembic.ini                 # Alembic 配置（连接串走环境变量，不写死）
├── ddl/                        # 建表 DDL（单一真源，可直接 psql -f 应用）
│   ├── 01_platform_identity.sql
│   ├── 02_platform_clearing.sql
│   └── 03_scenario_referral.sql
└── migrations/                 # Alembic 迁移（执行 ddl/*.sql，与之同源不双轨）
    ├── env.py
    ├── script.py.mako
    └── versions/
        ├── 0001_platform_identity.py
        ├── 0002_platform_clearing.py
        └── 0003_scenario_referral.py
```

> 迁移脚本只是按版本顺序执行 `ddl/*.sql` 并管理升降级，**DDL 本身是唯一真源**，
> 避免手写 DDL 与 ORM autogenerate 双轨漂移。

## 运行

先装迁移工具依赖（独立 `db` 依赖组，不进业务服务运行镜像）：

```bash
uv sync --group db
```

连接串由环境变量注入（私有化要求：密钥不进仓库/镜像）。本地 dev 库由
`infra/docker/compose.dev.yml` 提供（账号/密码/库 = dev/dev/hospital）。

Linux/macOS：

```bash
export DATABASE_URL="postgresql+psycopg://dev:dev@localhost:5432/hospital"
cd infra/db
uv run alembic upgrade head        # 建库到最新
uv run alembic downgrade base      # 全部回滚（DROP SCHEMA CASCADE）
uv run alembic history             # 查看版本链
```

Windows PowerShell：

```powershell
$env:DATABASE_URL = "postgresql+psycopg://dev:dev@localhost:5432/hospital"
cd infra\db
uv run alembic upgrade head
```

> ⚠️ Windows 注意：`alembic.ini` 必须保持**纯 ASCII**。Windows 上 configparser 用系统
> 区域编码（中文系统是 GBK）读 ini，含中文注释会报 `UnicodeDecodeError`。说明性中文写在本 README，不要写进 ini。

离线生成 SQL（院内不连库审阅/执行）：

```bash
uv run alembic upgrade head --sql > build.sql
```

或绕过 Alembic 直接按序应用 DDL：

```bash
psql "$DATABASE_URL" -f ddl/01_platform_identity.sql
psql "$DATABASE_URL" -f ddl/02_platform_clearing.sql
psql "$DATABASE_URL" -f ddl/03_scenario_referral.sql
```

## 约定

- **版本链**：平台域先行（identity → clearing），场景域依赖平台域（referral 在其后）。
  新场景的建表迁移挂在已有版本之后，schema 用 `scenario_<name>`。
- **公共字段**：业务表统一 `id/org_id/dept_code/created_at/updated_at/created_by/updated_by/`
  `is_deleted/row_version`（与 `py_common.models.CommonColumns` 对应）。
- **数据权限**：`org_id`+`dept_code` 驱动；跨机构可见性走 `platform_identity.record_grant`。
- **台账**：`income_split`/`settlement_ledger`/`credit_ledger` 只追加，纠错走红冲。
- **加密**：患者敏感字段在 `platform_patient`（后续迁移）用 `pgcrypto` 加密，密钥运行时注入。
