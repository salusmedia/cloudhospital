"""scenario_referral: 转诊一件事（首个端到端场景样例）

Revision ID: 0003_scenario_referral
Revises: 0002_platform_clearing
Create Date: 2026-06-18
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0003_scenario_referral"
down_revision = "0002_platform_clearing"
branch_labels = None
depends_on = None

_DDL_DIR = Path(__file__).resolve().parents[2] / "ddl"


def _run(sql_file: str) -> None:
    op.execute((_DDL_DIR / sql_file).read_text(encoding="utf-8"))


def upgrade() -> None:
    _run("03_scenario_referral.sql")
    op.execute("RESET search_path")


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS scenario_referral CASCADE")
