"""场景006 在线复诊 —— 互联网诊疗闭环：候诊→接诊→开方(AI审方)→结束(计酬)。

复用平台能力（验证多场景架构）：
- py-common：鉴权(require_cap)、数据权限(scope_filter)、审计、清分(split_income)。
- platform_clearing：计价规则与多方分账（原始 SQL 跨 schema 写入）。
- patient_id 只引用，不自建患者表。
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.core.config import settings
from app.db import get_db
from app.models import Consult, ConsultRx
from py_common import (
    AuthUser,
    audit_action,
    get_current_user,
    has_global_scope,
    require_cap,
    scope_filter,
)
from py_common.clearing import RateCard, split_income

router = APIRouter(prefix=settings.api_prefix, tags=["scenario-006"])


def _load(db: Session, no: str, user: AuthUser) -> Consult:
    c = db.scalar(select(Consult).where(Consult.consult_no == no, Consult.is_deleted.is_(False)))
    if c is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="复诊会话不存在")
    if not (has_global_scope(user) or c.dept_code in user.scopes):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="无权访问该会话")
    return c


class ConsultOut(BaseModel):
    consult_no: str
    patient_id: str
    dept_code: str
    status: str
    chief_complaint: str | None
    ai_triage: str | None


def _out(c: Consult) -> ConsultOut:
    return ConsultOut(
        consult_no=c.consult_no, patient_id=c.patient_id, dept_code=c.dept_code,
        status=c.status, chief_complaint=c.chief_complaint, ai_triage=c.ai_triage,
    )


@router.get("/consults", response_model=list[ConsultOut])
def list_consults(
    status_eq: str | None = Query(default=None, alias="status"),
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ConsultOut]:
    """候诊/接诊队列（按 scopes 数据权限过滤）。"""
    stmt = scope_filter(select(Consult), Consult, user).order_by(Consult.created_at)
    if status_eq:
        stmt = stmt.where(Consult.status == status_eq)
    rows = db.scalars(stmt).all()
    audit_action(user, action="list_consults", scenario=settings.scenario_id, extra={"count": len(rows)})
    return [_out(c) for c in rows]


@router.post("/consults/{no}/accept", response_model=ConsultOut)
def accept_consult(
    no: str,
    user: AuthUser = Depends(require_cap("teleconsult:treat")),
    db: Session = Depends(get_db),
) -> ConsultOut:
    """接诊（需能力 teleconsult:treat）。"""
    c = _load(db, no, user)
    if c.status != "waiting":
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"当前状态 {c.status} 不可接诊")
    c.status = "in_progress"
    c.accepted_by = user.user_id
    c.accepted_at = datetime.now(timezone.utc)
    audit_action(user, action="accept_consult", scenario=settings.scenario_id, patient_id=c.patient_id, target=no)
    db.flush()
    return _out(c)


class PrescribeIn(BaseModel):
    drug_name: str
    usage: str | None = None


class RxOut(BaseModel):
    drug_name: str
    usage: str | None
    ai_review: str
    review_note: str | None


_PLATFORM_AI_URL = "http://localhost:8103/api/platform-ai/rx-review"
_WARN_KEYWORDS = ("布洛芬", "双氯芬酸", "吲哚美辛")


def _call_platform_ai(drug_name: str, usage: str | None, user: AuthUser) -> tuple[str, str | None]:
    """调 platform-ai/rx-review；超时或失败时降级到本地规则。

    服务间走 localhost（同容器），转发 X-User-* 头保持身份链路。
    """
    try:
        resp = httpx.post(
            _PLATFORM_AI_URL,
            json={"drug_name": drug_name, "usage": usage},
            headers={
                "X-User-Id": user.user_id,
                "X-User-Name": user.name,
                "X-User-Roles": ",".join(user.roles),
                "X-User-Scopes": ",".join(user.scopes),
                "X-User-Caps": ",".join(user.caps),
            },
            timeout=4.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("result", "passed"), data.get("note")
    except Exception as exc:
        logger.warning("platform-ai 不可达，降级规则引擎: %s", exc)
        warn = any(k in drug_name for k in _WARN_KEYWORDS)
        review = "warn" if warn else "passed"
        note = "与抗血小板/抗凝用药存在相互作用风险，请复核" if warn else None
        return review, note


@router.post("/consults/{no}/prescribe", response_model=RxOut)
def prescribe(
    no: str, payload: PrescribeIn,
    user: AuthUser = Depends(require_cap("teleconsult:treat")),
    db: Session = Depends(get_db),
) -> RxOut:
    """开具电子处方（AI 审方由 platform-ai 服务提供，不可达时降级规则引擎）。"""
    c = _load(db, no, user)
    if c.status != "in_progress":
        raise HTTPException(status.HTTP_409_CONFLICT, detail="请先接诊再开方")
    review, note = _call_platform_ai(payload.drug_name, payload.usage, user)
    rx = ConsultRx(consult_no=no, drug_name=payload.drug_name, usage=payload.usage, ai_review=review, review_note=note)
    db.add(rx)
    audit_action(user, action="prescribe", scenario=settings.scenario_id, patient_id=c.patient_id, target=no)
    db.flush()
    return RxOut(drug_name=rx.drug_name, usage=rx.usage, ai_review=rx.ai_review, review_note=rx.review_note)


class SplitOut(BaseModel):
    payee_type: str
    amount: float


class FinishOut(BaseModel):
    consult_no: str
    status: str
    gross_amount: float
    splits: list[SplitOut]


@router.post("/consults/{no}/finish", response_model=FinishOut)
def finish_consult(
    no: str,
    user: AuthUser = Depends(require_cap("teleconsult:treat")),
    db: Session = Depends(get_db),
) -> FinishOut:
    """结束接诊 → 复用平台清分(platform_clearing)计酬并分账。"""
    c = _load(db, no, user)
    if c.status != "in_progress":
        raise HTTPException(status.HTTP_409_CONFLICT, detail="仅进行中的会话可结束")

    rate = db.execute(
        text("""SELECT unit_price,individual_ratio,dept_ratio,org_ratio,platform_ratio
                FROM platform_clearing.service_rate_card
                WHERE scenario_code=:s AND service_type='online_consult' AND status='active' LIMIT 1"""),
        {"s": settings.scenario_code},
    ).mappings().first()
    if rate is None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="未配置在线复诊计价规则")

    gross = Decimal(str(rate["unit_price"]))
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
                VALUES(:s,'online_consult',:u,:o,'in_hospital',:p,:g,'cleared') RETURNING event_id"""),
        {"s": settings.scenario_code, "u": user.user_id, "o": c.org_id, "p": c.patient_id, "g": gross},
    ).scalar()
    payee = {"individual": user.user_id, "dept": c.dept_code, "org": c.org_id, "platform": "platform"}
    for sp in splits:
        db.execute(
            text("INSERT INTO platform_clearing.income_split(event_id,payee_type,payee_id,amount) VALUES(:e,:t,:i,:a)"),
            {"e": event_id, "t": sp.payee_type, "i": payee[sp.payee_type], "a": sp.amount},
        )

    c.status = "finished"
    c.finished_at = datetime.now(timezone.utc)
    audit_action(user, action="finish_consult", scenario=settings.scenario_id, patient_id=c.patient_id, target=no)
    db.flush()
    return FinishOut(
        consult_no=no, status=c.status, gross_amount=float(gross),
        splits=[SplitOut(payee_type=s.payee_type, amount=float(s.amount)) for s in splits],
    )
