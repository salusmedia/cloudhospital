"""referral full: 知情同意/时间轴/下转方案/MDT/预警

Revision ID: 0006_referral_full
Revises: 0005_external_sources
Create Date: 2026-06-18
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0006_referral_full"
down_revision = "0005_external_sources"
branch_labels = None
depends_on = None

_DDL_DIR = Path(__file__).resolve().parents[2] / "ddl"


def _run(sql_file: str) -> None:
    op.execute((_DDL_DIR / sql_file).read_text(encoding="utf-8"))


def upgrade() -> None:
    _run("06_referral_full.sql")
    op.execute("RESET search_path")


def downgrade() -> None:
    for t in (
        "referral_alert", "mdt_opinion", "mdt_expert", "mdt_session",
        "downward_plan_drug", "downward_plan", "referral_track", "referral_consent",
    ):
        op.execute(f"DROP TABLE IF EXISTS scenario_referral.{t} CASCADE")
