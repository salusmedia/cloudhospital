"""platform_patient: 患者主数据（敏感字段 pgcrypto 加密）

Revision ID: 0004_platform_patient
Revises: 0003_scenario_referral
Create Date: 2026-06-18
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0004_platform_patient"
down_revision = "0003_scenario_referral"
branch_labels = None
depends_on = None

_DDL_DIR = Path(__file__).resolve().parents[2] / "ddl"


def _run(sql_file: str) -> None:
    op.execute((_DDL_DIR / sql_file).read_text(encoding="utf-8"))


def upgrade() -> None:
    _run("04_platform_patient.sql")
    op.execute("RESET search_path")


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS platform_patient CASCADE")
