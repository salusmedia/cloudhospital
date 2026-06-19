"""platform_clearing: 差异化计价 + 多方分账 + 个人清分账户

Revision ID: 0002_platform_clearing
Revises: 0001_platform_identity
Create Date: 2026-06-18
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0002_platform_clearing"
down_revision = "0001_platform_identity"
branch_labels = None
depends_on = None

_DDL_DIR = Path(__file__).resolve().parents[2] / "ddl"


def _run(sql_file: str) -> None:
    op.execute((_DDL_DIR / sql_file).read_text(encoding="utf-8"))


def upgrade() -> None:
    _run("02_platform_clearing.sql")
    op.execute("RESET search_path")


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS platform_clearing CASCADE")
