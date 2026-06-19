"""ORM 模型，映射到已迁移的真实表（见 infra/db/ddl/）。

- Referral 在本场景 schema `scenario_referral`，继承公共字段（含 org_id/dept_code，驱动数据权限）。
- 计价/分账三张表在平台域 `platform_clearing`，跨 schema 引用（同库，SQLAlchemy 原生支持）。
- 只存 patient_id 引用，不自建患者主数据（合规红线）。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from py_common.db import Base
from py_common.models import CommonColumns, uuid7


class Referral(Base, CommonColumns):
    __tablename__ = "referral"
    __table_args__ = {"schema": "scenario_referral"}

    ref_no: Mapped[str] = mapped_column(String(32), unique=True)
    patient_id: Mapped[str] = mapped_column(String(64))
    source_org: Mapped[str] = mapped_column(String(32))
    source_doctor: Mapped[str] = mapped_column(String(64))
    target_org: Mapped[str | None] = mapped_column(String(32))
    target_doctor: Mapped[str | None] = mapped_column(String(64))
    ref_type: Mapped[str] = mapped_column("type", String(16))  # type 是关键字，列名用 type
    risk_level: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16))
    appointment_slot: Mapped[str | None] = mapped_column(String(64))


class ServiceRateCard(Base):
    __tablename__ = "service_rate_card"
    __table_args__ = {"schema": "platform_clearing"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    scenario_code: Mapped[str] = mapped_column(String(32))
    service_type: Mapped[str] = mapped_column(String(64))
    applies_org_tier: Mapped[str] = mapped_column(String(16))
    applies_title_rank: Mapped[int] = mapped_column()
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    individual_ratio: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    dept_ratio: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    org_ratio: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    platform_ratio: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    floor_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    cap_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(16))


class IncomeEvent(Base):
    __tablename__ = "income_event"
    __table_args__ = {"schema": "platform_clearing"}

    event_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    scenario_code: Mapped[str] = mapped_column(String(32))
    service_type: Mapped[str] = mapped_column(String(64))
    performer_user_id: Mapped[str] = mapped_column(String(64))
    perform_org_id: Mapped[str] = mapped_column(String(32))
    engagement_mode: Mapped[str] = mapped_column(String(16))
    patient_id: Mapped[str | None] = mapped_column(String(64))
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    clearing_status: Mapped[str] = mapped_column(String(16), default="pending")


class IncomeSplit(Base):
    __tablename__ = "income_split"
    __table_args__ = {"schema": "platform_clearing"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    event_id: Mapped[uuid.UUID] = mapped_column()
    payee_type: Mapped[str] = mapped_column(String(16))
    payee_id: Mapped[str] = mapped_column(String(64))
    ratio: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))


# ---- 七节点积分链 / 个人服务信用账户（scenario_referral）----
class ReferralNode(Base):
    __tablename__ = "referral_node"
    __table_args__ = {"schema": "scenario_referral"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    ref_no: Mapped[str] = mapped_column(String(32))
    node: Mapped[str] = mapped_column(String(32))
    seq: Mapped[int] = mapped_column()
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    operator: Mapped[str | None] = mapped_column(String(64))


class CreditAccount(Base):
    __tablename__ = "credit_account"
    __table_args__ = {"schema": "scenario_referral"}

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    points: Mapped[int] = mapped_column(default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CreditLedger(Base):
    __tablename__ = "credit_ledger"
    __table_args__ = {"schema": "scenario_referral"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    user_id: Mapped[str] = mapped_column(String(64))
    ref_no: Mapped[str] = mapped_column(String(32))
    node: Mapped[str] = mapped_column(String(32))
    points: Mapped[int] = mapped_column()
    drg_amt: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    perf_amt: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    surplus_amt: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))


# ---- 完整转诊：五要素 / 资料 / 同意 / 时间轴 / 下转 / MDT / 预警 ----
_SR = {"schema": "scenario_referral"}


class ReferralCheck(Base):
    __tablename__ = "referral_check"
    __table_args__ = _SR
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    ref_no: Mapped[str] = mapped_column(String(32))
    item: Mapped[str] = mapped_column(String(64))
    passed: Mapped[bool] = mapped_column(Boolean, default=False)


class ReferralPackage(Base):
    __tablename__ = "referral_package"
    __table_args__ = _SR
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    ref_no: Mapped[str] = mapped_column(String(32))
    doc_type: Mapped[str] = mapped_column(String(32))
    source_report_id: Mapped[str | None] = mapped_column(String(64))
    mutual_recognition: Mapped[bool] = mapped_column(Boolean, default=False)


class ReferralConsent(Base):
    __tablename__ = "referral_consent"
    __table_args__ = _SR
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    ref_no: Mapped[str] = mapped_column(String(32))
    doc_name: Mapped[str] = mapped_column(String(64))
    seq: Mapped[int] = mapped_column(Integer, default=0)
    signed: Mapped[bool] = mapped_column(Boolean, default=False)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    signer: Mapped[str | None] = mapped_column(String(64))


class ReferralTrack(Base):
    __tablename__ = "referral_track"
    __table_args__ = _SR
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    ref_no: Mapped[str] = mapped_column(String(32))
    seq: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(64))
    detail: Mapped[str | None] = mapped_column(String(256))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    operator: Mapped[str | None] = mapped_column(String(64))


class DownwardPlan(Base):
    __tablename__ = "downward_plan"
    __table_args__ = _SR
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    ref_no: Mapped[str] = mapped_column(String(32))
    summary: Mapped[str | None] = mapped_column(String(512))
    review_plan: Mapped[str | None] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(16), default="issued")
    created_by: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DownwardPlanDrug(Base):
    __tablename__ = "downward_plan_drug"
    __table_args__ = _SR
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    plan_id: Mapped[uuid.UUID] = mapped_column()
    drug: Mapped[str] = mapped_column(String(128))
    usage: Mapped[str | None] = mapped_column(String(64))
    course: Mapped[str | None] = mapped_column(String(64))


class MdtSession(Base):
    __tablename__ = "mdt_session"
    __table_args__ = _SR
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    ref_no: Mapped[str | None] = mapped_column(String(32))
    topic: Mapped[str] = mapped_column(String(128))
    case_summary: Mapped[str | None] = mapped_column(String(512))
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), default="scheduled")
    host_user: Mapped[str | None] = mapped_column(String(64))
    org_id: Mapped[str | None] = mapped_column(String(32))
    dept_code: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class MdtExpert(Base):
    __tablename__ = "mdt_expert"
    __table_args__ = _SR
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    mdt_id: Mapped[uuid.UUID] = mapped_column()
    user_id: Mapped[str | None] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(64))
    dept: Mapped[str | None] = mapped_column(String(64))
    org: Mapped[str | None] = mapped_column(String(64))
    role: Mapped[str | None] = mapped_column(String(32))
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)


class MdtOpinion(Base):
    __tablename__ = "mdt_opinion"
    __table_args__ = _SR
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    mdt_id: Mapped[uuid.UUID] = mapped_column()
    user_id: Mapped[str | None] = mapped_column(String(64))
    name: Mapped[str | None] = mapped_column(String(64))
    opinion: Mapped[str] = mapped_column(String(1024))
    signed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ReferralAlert(Base):
    __tablename__ = "referral_alert"
    __table_args__ = _SR
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    ref_no: Mapped[str | None] = mapped_column(String(32))
    level: Mapped[str] = mapped_column(String(8))
    category: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(128))
    detail: Mapped[str | None] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(16), default="open")
    handled_by: Mapped[str | None] = mapped_column(String(64))
    handled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
