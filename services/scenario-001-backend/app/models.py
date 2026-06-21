"""ORM 模型（schema scenario_followup）。只存 patient_id 引用，不自建患者主数据。"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from py_common.db import Base
from py_common.models import CommonColumns


class FollowupPlan(Base, CommonColumns):
    __tablename__ = "followup_plan"
    __table_args__ = {"schema": "scenario_followup"}

    plan_no: Mapped[str] = mapped_column(String(32), unique=True)
    patient_id: Mapped[str] = mapped_column(String(64))
    plan_type: Mapped[str] = mapped_column(String(16), default="chronic")
    interval_days: Mapped[int] = mapped_column(Integer, default=30)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    note: Mapped[str | None] = mapped_column(String(256))
    # dept_code + org_id + is_deleted 继承自 CommonColumns


class FollowupRecord(Base, CommonColumns):
    __tablename__ = "followup_record"
    __table_args__ = {"schema": "scenario_followup"}

    plan_no: Mapped[str | None] = mapped_column(String(32))
    patient_id: Mapped[str] = mapped_column(String(64))
    visit_date: Mapped[date] = mapped_column(Date)
    method: Mapped[str] = mapped_column(String(16), default="phone")
    note: Mapped[str | None] = mapped_column(String(512))
    next_date: Mapped[date | None] = mapped_column(Date)
    doctor_id: Mapped[str | None] = mapped_column(String(64))
    # dept_code + org_id + is_deleted 继承自 CommonColumns
