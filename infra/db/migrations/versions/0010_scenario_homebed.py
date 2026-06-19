"""scenario_homebed: 场景002 家庭病床

Revision ID: 0010_scenario_homebed
Revises: 0009_platform_iot
Create Date: 2026-06-18
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0010_scenario_homebed"
down_revision = "0009_platform_iot"
branch_labels = None
depends_on = None

_DDL_DIR = Path(__file__).resolve().parents[2] / "ddl"


def _run(sql_file: str) -> None:
    op.execute((_DDL_DIR / sql_file).read_text(encoding="utf-8"))


def upgrade() -> None:
    _run("10_scenario_homebed.sql")
    op.execute("RESET search_path")


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS scenario_homebed CASCADE")
