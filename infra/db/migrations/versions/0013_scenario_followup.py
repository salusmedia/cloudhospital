"""scenario_followup: 场景001 在线随访（随访计划 + 随访记录）

Revision ID: 0013_scenario_followup
Revises: 0012_consent_file
Create Date: 2026-06-21
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0013_scenario_followup"
down_revision = "0012_consent_file"
branch_labels = None
depends_on = None

_DDL_DIR = Path(__file__).resolve().parents[2] / "ddl"


def _run(sql_file: str) -> None:
    op.execute((_DDL_DIR / sql_file).read_text(encoding="utf-8"))


def upgrade() -> None:
    _run("13_scenario_followup.sql")
    op.execute("RESET search_path")


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS scenario_followup CASCADE")
