"""scenario_teleconsult: 场景006 在线复诊

Revision ID: 0008_scenario_teleconsult
Revises: 0007_platform_archive
Create Date: 2026-06-18
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0008_scenario_teleconsult"
down_revision = "0007_platform_archive"
branch_labels = None
depends_on = None

_DDL_DIR = Path(__file__).resolve().parents[2] / "ddl"


def _run(sql_file: str) -> None:
    op.execute((_DDL_DIR / sql_file).read_text(encoding="utf-8"))


def upgrade() -> None:
    _run("08_scenario_teleconsult.sql")
    op.execute("RESET search_path")


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS scenario_teleconsult CASCADE")
