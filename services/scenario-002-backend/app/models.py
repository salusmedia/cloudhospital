"""ORM 模型（schema scenario_homebed）。只存 patient_id 引用。

体征复用 platform_iot、计酬复用 platform_clearing（均原始 SQL 跨 schema）。
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from py_common.db import Base
from py_common.models import CommonColumns, uuid7


class Bed(Base, CommonColumns):
    __tablename__ = "bed"
    __table_args__ = {"schema": "scenario_homebed"}

    bed_no: Mapped[str] = mapped_column(String(32), unique=True)
    patient_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="reviewing")
    care_level: Mapped[str | None] = mapped_column(String(16))
    attending_doctor: Mapped[str | None] = mapped_column(String(64))
    admit_date: Mapped[date | None] = mapped_column(Date)
    discharge_date: Mapped[date | None] = mapped_column(Date)
    review_note: Mapped[str | None] = mapped_column(String(128))


class CareTask(Base):
    __tablename__ = "care_task"
    __table_args__ = {"schema": "scenario_homebed"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    bed_no: Mapped[str] = mapped_column(String(32))
    type: Mapped[str] = mapped_column(String(16))
    content: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(8), default="todo")
    assignee: Mapped[str | None] = mapped_column(String(64))
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class BedMessage(Base):
    __tablename__ = "bed_message"
    __table_args__ = {"schema": "scenario_homebed"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    bed_no: Mapped[str] = mapped_column(String(32))
    sender: Mapped[str] = mapped_column(String(64))
    sender_role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
