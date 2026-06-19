"""scenario_homebed: 远程问诊消息

Revision ID: 0011_homebed_message
Revises: 0010_scenario_homebed
Create Date: 2026-06-18
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0011_homebed_message"
down_revision = "0010_scenario_homebed"
branch_labels = None
depends_on = None

_DDL_DIR = Path(__file__).resolve().parents[2] / "ddl"


def upgrade() -> None:
    op.execute((_DDL_DIR / "11_homebed_message.sql").read_text(encoding="utf-8"))
    op.execute("RESET search_path")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS scenario_homebed.bed_message CASCADE")
