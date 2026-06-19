"""external sources: 医保 / 检查互认目录 / 号源（开发期种子数据填充）

Revision ID: 0005_external_sources
Revises: 0004_platform_patient
Create Date: 2026-06-18
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0005_external_sources"
down_revision = "0004_platform_patient"
branch_labels = None
depends_on = None

_DDL_DIR = Path(__file__).resolve().parents[2] / "ddl"


def _run(sql_file: str) -> None:
    op.execute((_DDL_DIR / sql_file).read_text(encoding="utf-8"))


def upgrade() -> None:
    _run("05_external_sources.sql")
    op.execute("RESET search_path")


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS platform_insurance CASCADE")
    op.execute("DROP SCHEMA IF EXISTS platform_dict CASCADE")
    op.execute("DROP SCHEMA IF EXISTS platform_appointment CASCADE")
