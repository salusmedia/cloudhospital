"""MDT 多学科会诊接口。创建会诊室、查看专家与病例、提交署名会诊意见。"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.models import MdtExpert, MdtOpinion, MdtSession
from py_common import AuthUser, audit_action, get_current_user, require_cap

router = APIRouter(prefix=f"{settings.api_prefix}/mdt", tags=["scenario-019-mdt"])


class ExpertIn(BaseModel):
    name: str
    dept: str | None = None
    org: str | None = None
    role: str | None = "参与"
    user_id: str | None = None
    confirmed: bool = False


class MdtCreateIn(BaseModel):
    topic: str
    case_summary: str | None = None
    ref_no: str | None = None
    experts: list[ExpertIn] = []


class ExpertOut(ExpertIn):
    id: str


class OpinionOut(BaseModel):
    name: str | None
    opinion: str
    signed_at: datetime


class MdtOut(BaseModel):
    id: str
    topic: str
    case_summary: str | None
    ref_no: str | None
    status: str
    host_user: str | None
    experts: list[ExpertOut]
    opinions: list[OpinionOut]


@router.get("", response_model=list[MdtOut])
def list_mdt(user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> list[MdtOut]:
    sessions = db.scalars(select(MdtSession).order_by(MdtSession.created_at.desc())).all()
    return [_to_out(db, s) for s in sessions]


@router.post("", response_model=MdtOut, status_code=status.HTTP_201_CREATED)
def create_mdt(
    payload: MdtCreateIn,
    user: AuthUser = Depends(require_cap("referral:receive", "referral:initiate")),
    db: Session = Depends(get_db),
) -> MdtOut:
    s = MdtSession(
        topic=payload.topic, case_summary=payload.case_summary, ref_no=payload.ref_no,
        host_user=user.user_id, org_id=user.scopes[0] if user.scopes else None,
        dept_code=user.scopes[0] if user.scopes else None,
    )
    db.add(s)
    db.flush()
    for e in payload.experts:
        db.add(MdtExpert(mdt_id=s.id, name=e.name, dept=e.dept, org=e.org, role=e.role, user_id=e.user_id, confirmed=e.confirmed))
    audit_action(user, action="create_mdt", scenario=settings.scenario_id, target=str(s.id))
    db.flush()
    return _to_out(db, s)


@router.get("/{mdt_id}", response_model=MdtOut)
def get_mdt(mdt_id: str, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> MdtOut:
    s = db.get(MdtSession, mdt_id)
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="会诊不存在")
    return _to_out(db, s)


class OpinionIn(BaseModel):
    opinion: str


@router.post("/{mdt_id}/opinion", response_model=OpinionOut, status_code=status.HTTP_201_CREATED)
def submit_opinion(
    mdt_id: str, payload: OpinionIn,
    user: AuthUser = Depends(require_cap("referral:receive", "referral:initiate")),
    db: Session = Depends(get_db),
) -> OpinionOut:
    s = db.get(MdtSession, mdt_id)
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="会诊不存在")
    op = MdtOpinion(mdt_id=s.id, user_id=user.user_id, name=user.name, opinion=payload.opinion)
    db.add(op)
    s.status = "done"
    audit_action(user, action="submit_mdt_opinion", scenario=settings.scenario_id, target=str(mdt_id))
    db.flush()
    return OpinionOut(name=op.name, opinion=op.opinion, signed_at=op.signed_at)


def _to_out(db: Session, s: MdtSession) -> MdtOut:
    experts = db.scalars(select(MdtExpert).where(MdtExpert.mdt_id == s.id)).all()
    opinions = db.scalars(select(MdtOpinion).where(MdtOpinion.mdt_id == s.id).order_by(MdtOpinion.signed_at)).all()
    return MdtOut(
        id=str(s.id), topic=s.topic, case_summary=s.case_summary, ref_no=s.ref_no, status=s.status,
        host_user=s.host_user,
        experts=[ExpertOut(id=str(e.id), name=e.name, dept=e.dept, org=e.org, role=e.role, user_id=e.user_id, confirmed=e.confirmed) for e in experts],
        opinions=[OpinionOut(name=o.name, opinion=o.opinion, signed_at=o.signed_at) for o in opinions],
    )
