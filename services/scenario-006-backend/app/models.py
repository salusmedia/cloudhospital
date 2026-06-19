"""ORM 模型（schema scenario_teleconsult）。只存 patient_id 引用，不自建患者主数据。

计价/分账复用平台域 platform_clearing（本场景用原始 SQL 写入，math 用 py_common.split_income）。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from py_common.db import Base
from py_common.models import CommonColumns, uuid7


class Consult(Base, CommonColumns):
    __tablename__ = "consult"
    __table_args__ = {"schema": "scenario_teleconsult"}

    consult_no: Mapped[str] = mapped_column(String(32), unique=True)
    patient_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="waiting")
    chief_complaint: Mapped[str | None] = mapped_column(String(256))
    ai_triage: Mapped[str | None] = mapped_column(String(8))
    accepted_by: Mapped[str | None] = mapped_column(String(64))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ConsultRx(Base):
    __tablename__ = "consult_rx"
    __table_args__ = {"schema": "scenario_teleconsult"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    consult_no: Mapped[str] = mapped_column(String(32))
    drug_name: Mapped[str] = mapped_column(String(128))
    usage: Mapped[str | None] = mapped_column(String(64))
    ai_review: Mapped[str] = mapped_column(String(16), default="passed")
    review_note: Mapped[str | None] = mapped_column(String(128))
