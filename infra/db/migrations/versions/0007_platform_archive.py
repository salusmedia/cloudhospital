"""platform_archive: 健康档案（就诊/诊断/检验影像/处方）

Revision ID: 0007_platform_archive
Revises: 0006_referral_full
Create Date: 2026-06-18
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0007_platform_archive"
down_revision = "0006_referral_full"
branch_labels = None
depends_on = None

_DDL_DIR = Path(__file__).resolve().parents[2] / "ddl"


def _run(sql_file: str) -> None:
    op.execute((_DDL_DIR / sql_file).read_text(encoding="utf-8"))


def upgrade() -> None:
    _run("07_platform_archive.sql")
    op.execute("RESET search_path")


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS platform_archive CASCADE")
