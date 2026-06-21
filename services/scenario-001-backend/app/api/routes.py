"""场景 001 · 在线随访 —— 随访计划与随访记录管理。

合规要点：
- 鉴权：Depends(get_current_user)，由网关注入身份；越权返回 403。
- 数据权限：scope_filter 按 user.scopes（科室代码）过滤，只返回有权数据（最小权限）。
- 审计：所有查询/写入患者数据必须落 audit_action。
- 患者主数据不自存：只持 patient_id，敏感信息走 platform-patient HTTP 接口。
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.models import FollowupPlan, FollowupRecord
from py_common import (
    AuthUser,
    audit_action,
    get_current_user,
    has_global_scope,
    scope_filter,
)

router = APIRouter(prefix=settings.api_prefix, tags=["scenario-001"])


# ---- 响应模型 ---------------------------------------------------------------

class FollowupRecordOut(BaseModel):
    id: str
    patient_id: str
    plan_no: str | None
    dept_code: str
    visit_date: date
    method: str
    note: str | None
    next_date: date | None
    doctor_id: str | None


class FollowupPage(BaseModel):
    items: list[FollowupRecordOut]
    total: int
    page: int
    page_size: int


class FollowupPlanOut(BaseModel):
    id: str
    plan_no: str
    patient_id: str
    dept_code: str
    plan_type: str
    interval_days: int
    start_date: date
    end_date: date | None
    note: str | None


# ---- 查询接口 ---------------------------------------------------------------

@router.get("/followups", response_model=FollowupPage)
def list_followups(
    on: date | None = Query(default=None, description="按随访日期过滤（YYYY-MM-DD）"),
    dept: str | None = Query(default=None, description="按科室代码过滤"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FollowupPage:
    """查询随访记录（按科室数据权限过滤）。"""
    stmt = scope_filter(select(FollowupRecord), FollowupRecord, user).order_by(
        FollowupRecord.visit_date.desc()
    )
    if on:
        stmt = stmt.where(FollowupRecord.visit_date == on)
    if dept:
        stmt = stmt.where(FollowupRecord.dept_code == dept)

    all_rows = db.scalars(stmt).all()
    total = len(all_rows)
    page_rows = all_rows[(page - 1) * page_size : page * page_size]

    audit_action(
        user,
        action="list_followups",
        scenario=settings.scenario_id,
        result="ok",
        extra={"count": total, "on": on.isoformat() if on else None},
    )
    return FollowupPage(items=[_rec_out(r) for r in page_rows], total=total, page=page, page_size=page_size)


@router.get("/followups/{record_id}", response_model=FollowupRecordOut)
def get_followup(
    record_id: str,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FollowupRecordOut:
    """查询单条随访记录。"""
    row = db.scalar(
        select(FollowupRecord).where(
            FollowupRecord.id == record_id,
            FollowupRecord.is_deleted.is_(False),
        )
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="记录不存在")
    if not (has_global_scope(user) or row.dept_code in user.scopes):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="无权访问该患者记录")

    audit_action(
        user, action="get_followup", scenario=settings.scenario_id,
        patient_id=row.patient_id, target=record_id,
    )
    return _rec_out(row)


# ---- 写入接口 ---------------------------------------------------------------

class FollowupRecordIn(BaseModel):
    patient_id: str
    dept_code: str | None = None
    visit_date: date
    method: str = "phone"         # phone / video / onsite
    note: str | None = None
    next_date: date | None = None
    plan_no: str | None = None


@router.post("/followups", response_model=FollowupRecordOut, status_code=status.HTTP_201_CREATED)
def create_followup(
    payload: FollowupRecordIn,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FollowupRecordOut:
    """新增一条随访记录。"""
    dept = payload.dept_code or (user.scopes[0] if user.scopes else None)
    if not dept or not (has_global_scope(user) or dept in user.scopes):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="无权在该科室写入随访记录")

    rec = FollowupRecord(
        patient_id=payload.patient_id,
        dept_code=dept,
        org_id=user.scopes[0] if user.scopes else "default",
        visit_date=payload.visit_date,
        method=payload.method,
        note=payload.note,
        next_date=payload.next_date,
        plan_no=payload.plan_no,
        doctor_id=user.user_id,
        created_by=user.user_id,
        updated_by=user.user_id,
    )
    db.add(rec)
    db.flush()
    audit_action(
        user, action="create_followup", scenario=settings.scenario_id,
        patient_id=payload.patient_id, target=str(rec.id),
    )
    return _rec_out(rec)


# ---- 随访计划 ---------------------------------------------------------------

@router.get("/plans", response_model=list[FollowupPlanOut])
def list_plans(
    patient_id: str | None = Query(default=None),
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[FollowupPlanOut]:
    """查询随访计划列表（按科室权限过滤）。"""
    stmt = scope_filter(select(FollowupPlan), FollowupPlan, user).order_by(
        FollowupPlan.start_date.desc()
    )
    if patient_id:
        stmt = stmt.where(FollowupPlan.patient_id == patient_id)
    rows = db.scalars(stmt).all()
    audit_action(user, action="list_plans", scenario=settings.scenario_id, extra={"count": len(rows)})
    return [_plan_out(p) for p in rows]


# ---- 工具函数 ---------------------------------------------------------------

def _rec_out(r: FollowupRecord) -> FollowupRecordOut:
    return FollowupRecordOut(
        id=str(r.id),
        patient_id=r.patient_id,
        plan_no=r.plan_no,
        dept_code=r.dept_code,
        visit_date=r.visit_date,
        method=r.method,
        note=r.note,
        next_date=r.next_date,
        doctor_id=r.doctor_id,
    )


def _plan_out(p: FollowupPlan) -> FollowupPlanOut:
    return FollowupPlanOut(
        id=str(p.id),
        plan_no=p.plan_no,
        patient_id=p.patient_id,
        dept_code=p.dept_code,
        plan_type=p.plan_type,
        interval_days=p.interval_days,
        start_date=p.start_date,
        end_date=p.end_date,
        note=p.note,
    )
