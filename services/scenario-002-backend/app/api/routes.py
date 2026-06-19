"""场景002 家庭病床 —— 建床/准入审核/体征监测/护理任务/出院结算。

复用平台能力（多场景架构）：
- py-common：鉴权(require_cap)、数据权限(scope_filter)、审计、清分(split_income)。
- platform_iot：体征最新值与异常预警（原始 SQL 跨 schema 读）。
- platform_clearing：出院护理费计酬分账。
- patient_id 只引用，不自建患者表。
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.models import Bed, BedMessage, CareTask
from py_common import (
    AuthUser,
    audit_action,
    get_current_user,
    has_global_scope,
    require_cap,
    scope_filter,
)
from py_common.clearing import RateCard, split_income

router = APIRouter(prefix=settings.api_prefix, tags=["scenario-002"])

_CARE = require_cap("homebed:manage")


def _load(db: Session, no: str, user: AuthUser) -> Bed:
    b = db.scalar(select(Bed).where(Bed.bed_no == no, Bed.is_deleted.is_(False)))
    if b is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="病床不存在")
    if not (has_global_scope(user) or b.dept_code in user.scopes):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="无权访问该病床")
    return b


class BedOut(BaseModel):
    bed_no: str
    patient_id: str
    status: str
    care_level: str | None
    attending_doctor: str | None
    admit_date: date | None


def _out(b: Bed) -> BedOut:
    return BedOut(
        bed_no=b.bed_no, patient_id=b.patient_id, status=b.status,
        care_level=b.care_level, attending_doctor=b.attending_doctor, admit_date=b.admit_date,
    )


# ---------- 建床 / 准入审核 ----------
class BedCreateIn(BaseModel):
    patient_id: str
    care_level: str = "二级护理"
    attending_doctor: str | None = None
    dept_code: str | None = None


@router.post("/beds", response_model=BedOut, status_code=status.HTTP_201_CREATED)
def create_bed(payload: BedCreateIn, user: AuthUser = Depends(_CARE), db: Session = Depends(get_db)) -> BedOut:
    """申请建床 → 进入准入审核（reviewing）。"""
    dept = payload.dept_code or (user.scopes[0] if user.scopes else None)
    if dept is None or not (has_global_scope(user) or dept in user.scopes):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="无权在该科室建床")
    seq = db.scalar(text("SELECT count(*)+1 FROM scenario_homebed.bed")) or 1
    bed_no = f"HB-{int(seq):04d}"
    b = Bed(
        bed_no=bed_no, patient_id=payload.patient_id, status="reviewing",
        care_level=payload.care_level, attending_doctor=payload.attending_doctor or user.user_id,
        org_id="wzcvh", dept_code=dept, created_by=user.user_id,
    )
    db.add(b)
    db.flush()
    audit_action(user, action="create_bed", scenario=settings.scenario_id, patient_id=payload.patient_id, target=bed_no)
    return _out(b)


class ReviewIn(BaseModel):
    approved: bool = True
    note: str | None = None


@router.post("/beds/{no}/review", response_model=BedOut)
def review_bed(no: str, payload: ReviewIn, user: AuthUser = Depends(_CARE), db: Session = Depends(get_db)) -> BedOut:
    """准入审核：通过→建床(admitted)，否则 rejected。"""
    b = _load(db, no, user)
    if b.status != "reviewing":
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"当前状态 {b.status} 不可审核")
    if payload.approved:
        b.status = "admitted"
        b.admit_date = date.today()
    else:
        b.status = "rejected"
    b.review_note = payload.note
    audit_action(user, action="review_bed", scenario=settings.scenario_id, patient_id=b.patient_id, target=no)
    db.flush()
    return _out(b)


@router.get("/beds", response_model=list[BedOut])
def list_beds(
    status_eq: str | None = Query(default=None, alias="status"),
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[BedOut]:
    stmt = scope_filter(select(Bed), Bed, user).order_by(Bed.created_at.desc())
    if status_eq:
        stmt = stmt.where(Bed.status == status_eq)
    rows = db.scalars(stmt).all()
    audit_action(user, action="list_beds", scenario=settings.scenario_id, extra={"count": len(rows)})
    return [_out(b) for b in rows]


# ---------- 体征监测（复用 platform_iot） ----------
class VitalOut(BaseModel):
    metric: str
    value_text: str | None
    unit: str | None
    measured_at: datetime
    abnormal_flag: bool


class BedMonitor(BaseModel):
    bed_no: str
    patient_id: str
    latest: list[VitalOut]
    alert_count: int


@router.get("/beds/{no}/monitor", response_model=BedMonitor)
def bed_monitor(no: str, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> BedMonitor:
    """病床实时监测：从 platform_iot 取该患者最新体征 + 异常预警数。"""
    b = _load(db, no, user)
    latest = db.execute(
        text("""SELECT DISTINCT ON (metric) metric,value_text,unit,measured_at,abnormal_flag
                FROM platform_iot.vital_sign WHERE patient_id=:p ORDER BY metric, measured_at DESC"""),
        {"p": b.patient_id},
    ).mappings().all()
    alerts = db.scalar(
        text("SELECT count(*) FROM platform_iot.vital_sign WHERE patient_id=:p AND abnormal_flag"),
        {"p": b.patient_id},
    ) or 0
    audit_action(user, action="bed_monitor", scenario=settings.scenario_id, patient_id=b.patient_id, target=no)
    return BedMonitor(
        bed_no=no, patient_id=b.patient_id,
        latest=[VitalOut(**dict(x)) for x in latest], alert_count=int(alerts),
    )


# ---------- 护理任务 ----------
class TaskIn(BaseModel):
    type: str  # 查房/换药/体征采集/送药
    content: str | None = None
    assignee: str | None = None


class TaskOut(BaseModel):
    id: str
    type: str
    content: str | None
    status: str
    assignee: str | None


@router.get("/beds/{no}/tasks", response_model=list[TaskOut])
def list_tasks(no: str, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> list[TaskOut]:
    _load(db, no, user)
    rows = db.scalars(select(CareTask).where(CareTask.bed_no == no).order_by(CareTask.created_at)).all()
    return [TaskOut(id=str(t.id), type=t.type, content=t.content, status=t.status, assignee=t.assignee) for t in rows]


@router.post("/beds/{no}/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def add_task(no: str, payload: TaskIn, user: AuthUser = Depends(_CARE), db: Session = Depends(get_db)) -> TaskOut:
    b = _load(db, no, user)
    t = CareTask(bed_no=no, type=payload.type, content=payload.content, assignee=payload.assignee or user.user_id)
    db.add(t)
    db.flush()
    audit_action(user, action="add_care_task", scenario=settings.scenario_id, patient_id=b.patient_id, target=no)
    return TaskOut(id=str(t.id), type=t.type, content=t.content, status=t.status, assignee=t.assignee)


@router.post("/tasks/{task_id}/done", response_model=TaskOut)
def finish_task(task_id: str, user: AuthUser = Depends(_CARE), db: Session = Depends(get_db)) -> TaskOut:
    t = db.get(CareTask, task_id)
    if t is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="任务不存在")
    _load(db, t.bed_no, user)  # 数据权限校验
    t.status = "done"
    t.done_at = datetime.now(timezone.utc)
    audit_action(user, action="finish_care_task", scenario=settings.scenario_id, target=t.bed_no)
    db.flush()
    return TaskOut(id=str(t.id), type=t.type, content=t.content, status=t.status, assignee=t.assignee)


# ---------- 出院结算（复用 platform_clearing） ----------
class SplitOut(BaseModel):
    payee_type: str
    amount: float


class DischargeOut(BaseModel):
    bed_no: str
    status: str
    days: int
    gross_amount: float
    splits: list[SplitOut]


@router.post("/beds/{no}/discharge", response_model=DischargeOut)
def discharge(no: str, user: AuthUser = Depends(_CARE), db: Session = Depends(get_db)) -> DischargeOut:
    """出院 → 按住院天数 × 护理费计酬，复用平台清分分账。"""
    b = _load(db, no, user)
    if b.status != "admitted":
        raise HTTPException(status.HTTP_409_CONFLICT, detail="仅在床患者可出院")
    rate = db.execute(
        text("""SELECT unit_price,individual_ratio,dept_ratio,org_ratio,platform_ratio
                FROM platform_clearing.service_rate_card
                WHERE scenario_code=:s AND service_type='homebed_care' AND status='active' LIMIT 1"""),
        {"s": settings.scenario_code},
    ).mappings().first()
    if rate is None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="未配置家庭病床计价规则")

    days = max((date.today() - b.admit_date).days, 1) if b.admit_date else 1
    gross = Decimal(str(rate["unit_price"])) * days
    card = RateCard(
        individual_ratio=Decimal(str(rate["individual_ratio"])),
        dept_ratio=Decimal(str(rate["dept_ratio"])),
        org_ratio=Decimal(str(rate["org_ratio"])),
        platform_ratio=Decimal(str(rate["platform_ratio"])),
    )
    splits = split_income(gross, card)
    event_id = db.execute(
        text("""INSERT INTO platform_clearing.income_event
                 (scenario_code,service_type,performer_user_id,perform_org_id,engagement_mode,patient_id,gross_amount,clearing_status)
                VALUES(:s,'homebed_care',:u,:o,'in_hospital',:p,:g,'cleared') RETURNING event_id"""),
        {"s": settings.scenario_code, "u": user.user_id, "o": b.org_id, "p": b.patient_id, "g": gross},
    ).scalar()
    payee = {"individual": user.user_id, "dept": b.dept_code, "org": b.org_id, "platform": "platform"}
    for sp in splits:
        db.execute(
            text("INSERT INTO platform_clearing.income_split(event_id,payee_type,payee_id,amount) VALUES(:e,:t,:i,:a)"),
            {"e": event_id, "t": sp.payee_type, "i": payee[sp.payee_type], "a": sp.amount},
        )
    b.status = "discharged"
    b.discharge_date = date.today()
    audit_action(user, action="discharge_bed", scenario=settings.scenario_id, patient_id=b.patient_id, target=no)
    db.flush()
    return DischargeOut(
        bed_no=no, status=b.status, days=days, gross_amount=float(gross),
        splits=[SplitOut(payee_type=s.payee_type, amount=float(s.amount)) for s in splits],
    )


def _scope_clause(user: AuthUser, col: str) -> tuple[str, dict]:
    """按数据权限生成 SQL 片段；全局返回空。"""
    if has_global_scope(user):
        return "", {}
    return f" AND {col} = ANY(:_depts)", {"_depts": user.scopes or ["__none__"]}


# ---------- 运营看板 ----------
class HomebedDashboard(BaseModel):
    admitted: int
    reviewing: int
    pending_tasks: int
    alert_patients: int
    by_care_level: dict[str, int]


@router.get("/dashboard", response_model=HomebedDashboard)
def dashboard(user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> HomebedDashboard:
    sc, p = _scope_clause(user, "dept_code")
    bsc, _ = _scope_clause(user, "b.dept_code")
    base = "FROM scenario_homebed.bed WHERE is_deleted=false"
    admitted = db.scalar(text(f"SELECT count(*) {base} AND status='admitted'{sc}"), p) or 0
    reviewing = db.scalar(text(f"SELECT count(*) {base} AND status='reviewing'{sc}"), p) or 0
    pending = db.scalar(text(f"SELECT count(*) FROM scenario_homebed.care_task WHERE status='todo' AND bed_no IN (SELECT bed_no {base}{sc})"), p) or 0
    alert_pat = db.scalar(
        text(f"""SELECT count(DISTINCT b.patient_id) FROM scenario_homebed.bed b
                 JOIN platform_iot.vital_sign v ON v.patient_id=b.patient_id AND v.abnormal_flag
                 WHERE b.is_deleted=false AND b.status='admitted'{bsc}"""),
        p,
    ) or 0
    levels = db.execute(text(f"SELECT care_level, count(*) {base} AND status='admitted'{sc} GROUP BY care_level"), p).all()
    audit_action(user, action="homebed_dashboard", scenario=settings.scenario_id)
    return HomebedDashboard(
        admitted=admitted, reviewing=reviewing, pending_tasks=pending, alert_patients=alert_pat,
        by_care_level={(r[0] or "未分级"): r[1] for r in levels},
    )


# ---------- 质控 ----------
class HomebedQuality(BaseModel):
    task_total: int
    task_done: int
    completion_rate: float
    vitals_today: int
    abnormal_total: int


@router.get("/quality", response_model=HomebedQuality)
def quality(user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> HomebedQuality:
    sc, p = _scope_clause(user, "b.dept_code")
    bedset = f"(SELECT bed_no FROM scenario_homebed.bed b WHERE b.is_deleted=false{sc})"
    patset = f"(SELECT patient_id FROM scenario_homebed.bed b WHERE b.status='admitted' AND b.is_deleted=false{sc})"
    t_total = db.scalar(text(f"SELECT count(*) FROM scenario_homebed.care_task WHERE bed_no IN {bedset}"), p) or 0
    t_done = db.scalar(text(f"SELECT count(*) FROM scenario_homebed.care_task WHERE status='done' AND bed_no IN {bedset}"), p) or 0
    vitals_today = db.scalar(text(f"SELECT count(*) FROM platform_iot.vital_sign WHERE measured_at::date=CURRENT_DATE AND patient_id IN {patset}"), p) or 0
    abnormal = db.scalar(text(f"SELECT count(*) FROM platform_iot.vital_sign WHERE abnormal_flag AND patient_id IN {patset}"), p) or 0
    audit_action(user, action="homebed_quality", scenario=settings.scenario_id)
    return HomebedQuality(
        task_total=t_total, task_done=t_done,
        completion_rate=round(t_done / t_total, 3) if t_total else 0.0,
        vitals_today=vitals_today, abnormal_total=abnormal,
    )


# ---------- 远程问诊（医护↔患者图文） ----------
class MsgIn(BaseModel):
    content: str


class MsgOut(BaseModel):
    sender_role: str
    content: str
    created_at: datetime


@router.get("/beds/{no}/messages", response_model=list[MsgOut])
def list_messages(no: str, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> list[MsgOut]:
    _load(db, no, user)
    rows = db.scalars(select(BedMessage).where(BedMessage.bed_no == no).order_by(BedMessage.created_at)).all()
    return [MsgOut(sender_role=m.sender_role, content=m.content, created_at=m.created_at) for m in rows]


@router.post("/beds/{no}/messages", response_model=MsgOut, status_code=status.HTTP_201_CREATED)
def add_message(no: str, payload: MsgIn, user: AuthUser = Depends(_CARE), db: Session = Depends(get_db)) -> MsgOut:
    b = _load(db, no, user)
    role = "doctor" if "doctor" in user.roles else ("nurse" if "nurse" in user.roles else "doctor")
    m = BedMessage(bed_no=no, sender=user.user_id, sender_role=role, content=payload.content)
    db.add(m)
    db.flush()
    audit_action(user, action="bed_message", scenario=settings.scenario_id, patient_id=b.patient_id, target=no)
    return MsgOut(sender_role=role, content=m.content, created_at=m.created_at)
