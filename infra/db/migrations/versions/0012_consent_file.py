"""platform_consent + platform_file 域

Revision ID: 0012_consent_file
Revises: 0011_homebed_message
Create Date: 2026-06-18
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0012_consent_file"
down_revision = "0011_homebed_message"
branch_labels = None
depends_on = None

_DDL_DIR = Path(__file__).resolve().parents[2] / "ddl"


def upgrade() -> None:
    op.execute((_DDL_DIR / "12_consent_file.sql").read_text(encoding="utf-8"))
    op.execute("RESET search_path")


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS platform_consent CASCADE")
    op.execute("DROP SCHEMA IF EXISTS platform_file CASCADE")
