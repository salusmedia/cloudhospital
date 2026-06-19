"""platform_identity: 机构/科室/用户/RBAC/数据权限/场景授权/医护身份

Revision ID: 0001_platform_identity
Revises:
Create Date: 2026-06-18
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0001_platform_identity"
down_revision = None
branch_labels = None
depends_on = None

_DDL_DIR = Path(__file__).resolve().parents[2] / "ddl"


def _run(sql_file: str) -> None:
    op.execute((_DDL_DIR / sql_file).read_text(encoding="utf-8"))


def upgrade() -> None:
    # pgcrypto 提供 gen_random_uuid()（PG13+ 核心已内置，保险起见显式启用）
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    _run("01_platform_identity.sql")
    # DDL 里的 SET search_path 会切走连接搜索路径，复位以免影响 alembic_version 写入
    op.execute("RESET search_path")


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS platform_identity CASCADE")
