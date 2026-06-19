"""platform_iot: 体征监测域（设备实时回传 + 异常判定）

Revision ID: 0009_platform_iot
Revises: 0008_scenario_teleconsult
Create Date: 2026-06-18
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0009_platform_iot"
down_revision = "0008_scenario_teleconsult"
branch_labels = None
depends_on = None

_DDL_DIR = Path(__file__).resolve().parents[2] / "ddl"


def _run(sql_file: str) -> None:
    op.execute((_DDL_DIR / sql_file).read_text(encoding="utf-8"))


def upgrade() -> None:
    _run("09_platform_iot.sql")
    op.execute("RESET search_path")


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS platform_iot CASCADE")
