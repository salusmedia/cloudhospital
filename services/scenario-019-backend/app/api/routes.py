"""场景 019 · 转诊一件事 —— 对外接口。

演示三件套端到端落到真实数据库：
- scope_filter：列转诊单时按 user.scopes（科室）过滤，医生只看本科室（数据权限）。
- require_cap：接收转诊需场景能力 referral:receive，没有则 403（场景级最小权限）。
- split_income：接收转诊算一笔"接收协同服务"收入，按计价规则 4 方分账并落库。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.models import (
    CreditAccount,
    CreditLedger,
    IncomeEvent,
    IncomeSplit,
    Referral,
    ReferralNode,
    ServiceRateCard,
)
from py_common import (
    AuthUser,
    audit_action,
    get_current_user,
    has_global_scope,
    require_cap,
    scope_filter,
)
from py_common.clearing import RateCard, split_income

# 七节点积分链：节点代码 → 积分（整数，合计 100）。来源 V10 激励演示 ISTEPS。
NODE_POINTS: dict[str, int] = {
    "first_visit": 15,    # 首诊评估
    "package": 10,        # 资料打包
    "apply": 5,           # 转诊申请
    "accept": 38,         # 接收确认
    "downward_plan": 12,  # 下转方案
    "continue": 8,        # 接续确认
    "followup": 12,       # 随访执行
}
# 积分单价（元/分）。演示固定值，落在 V10 的保底 1.5 / 封顶 3.5 之间。
POINT_UNIT = Decimal("2.0")

router = APIRouter(prefix=settings.api_prefix, tags=["scenario-019"])


@router.get("/ping")
async def ping() -> dict[str, str]:
    return {"scenario": settings.scenario_id, "message": "pong"}


# ---- 契约模型 ----
class ReferralOut(BaseModel):
    ref_no: str
    patient_id: str
    dept_code: str
    type: str
    risk_level: str
    status: str


class SplitOut(BaseModel):
    payee_type: str
    payee_id: str
    amount: float


class ReceiveOut(BaseModel):
    ref_no: str
    status: str
    gross_amount: float
    splits: list[SplitOut]


@router.get("/referrals", response_model=list[ReferralOut])
def list_referrals(
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ReferralOut]:
    """列出转诊单——仅返回当前用户有权科室的数据（scope_filter 兜底数据权限）。"""
    stmt = scope_filter(select(Referral), Referral, user)
    rows = db.scalars(stmt).all()
    audit_action(
        user,
        action="list_referrals",
        scenario=settings.scenario_id,
        extra={"count": len(rows)},
    )
    return [
        ReferralOut(
            ref_no=r.ref_no,
            patient_id=r.patient_id,
            dept_code=r.dept_code,
            type=r.ref_type,
            risk_level=r.risk_level,
            status=r.status,
        )
        for r in rows
    ]


class ReferralCreateIn(BaseModel):
    patient_id: str
    type: str = "up"  # up上转/down下转/flat平转/emergency急诊/mdt
    risk_level: str = "yellow"  # red/yellow/green/critical
    dept_code: str | None = None  # 默认取当前用户首个 scope
    source_org: str = "community-wt"
    target_org: str | None = "wzcvh"


@router.post("/referrals", response_model=ReferralOut, status_code=status.HTTP_201_CREATED)
def create_referral(
    payload: ReferralCreateIn,
    user: AuthUser = Depends(require_cap("referral:initiate")),
    db: Session = Depends(get_db),
) -> ReferralOut:
    """发起转诊单（需能力 referral:initiate）。归属科室须在本人数据权限内。"""
    dept = payload.dept_code or (user.scopes[0] if user.scopes else None)
    if dept is None or not (has_global_scope(user) or dept in user.scopes):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="无权在该科室发起转诊")

    ref_no = f"ZZ-{datetime.now(timezone.utc):%Y%m%d}-{uuid.uuid4().hex[:6]}"
    ref = Referral(
        ref_no=ref_no,
        patient_id=payload.patient_id,
        source_org=payload.source_org,
        source_doctor=user.user_id,
        target_org=payload.target_org,
        target_doctor=None,
        ref_type=payload.type,
        risk_level=payload.risk_level,
        status="applying",
        org_id=payload.target_org or "wzcvh",
        dept_code=dept,
        created_by=user.user_id,
    )
    db.add(ref)
    db.flush()
    audit_action(
        user, action="create_referral", scenario=settings.scenario_id,
        patient_id=payload.patient_id, target=ref_no,
    )
    return ReferralOut(
        ref_no=ref.ref_no, patient_id=ref.patient_id, dept_code=ref.dept_code,
        type=ref.ref_type, risk_level=ref.risk_level, status=ref.status,
    )


@router.post("/referrals/{ref_no}/receive", response_model=ReceiveOut)
def receive_referral(
    ref_no: str,
    user: AuthUser = Depends(require_cap("referral:receive")),
    db: Session = Depends(get_db),
) -> ReceiveOut:
    """接收上转：更新状态 + 按计价规则把"接收协同服务"收入 4 方分账落库。"""
    ref = db.scalar(
        select(Referral).where(
            Referral.ref_no == ref_no, Referral.is_deleted.is_(False)
        )
    )
    if ref is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="转诊单不存在")
    # 数据权限：接收方必须有该科室 scope
    if not (has_global_scope(user) or ref.dept_code in user.scopes):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="无权接收该转诊单")

    # 取计价规则（按场景+服务类型）
    rate_row = db.scalar(
        select(ServiceRateCard).where(
            ServiceRateCard.scenario_code == settings.scenario_code,
            ServiceRateCard.service_type == "referral_receive",
            ServiceRateCard.status == "active",
        )
    )
    if rate_row is None:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, detail="未配置接收转诊的计价规则"
        )

    rate = RateCard(
        individual_ratio=rate_row.individual_ratio,
        dept_ratio=rate_row.dept_ratio,
        org_ratio=rate_row.org_ratio,
        platform_ratio=rate_row.platform_ratio,
        floor_price=rate_row.floor_price,
        cap_price=rate_row.cap_price,
    )
    gross = rate_row.unit_price
    splits = split_income(gross, rate, perf_coef=1)

    # 落库：更新转诊单状态 + 写收入事件与分账明细
    ref.status = "received"
    ref.updated_by = user.user_id

    event = IncomeEvent(
        scenario_code=settings.scenario_code,
        service_type="referral_receive",
        performer_user_id=user.user_id,
        perform_org_id=ref.target_org or ref.org_id,
        engagement_mode="in_hospital",
        patient_id=ref.patient_id,
        gross_amount=gross,
        clearing_status="cleared",
    )
    db.add(event)
    db.flush()  # 拿到 event_id

    payee_of = {
        "individual": user.user_id,
        "dept": ref.dept_code,
        "org": ref.target_org or ref.org_id,
        "platform": "platform",
    }
    for s in splits:
        db.add(
            IncomeSplit(
                event_id=event.event_id,
                payee_type=s.payee_type,
                payee_id=payee_of[s.payee_type],
                amount=s.amount,
            )
        )

    audit_action(
        user,
        action="receive_referral",
        scenario=settings.scenario_id,
        patient_id=ref.patient_id,
        target=ref_no,
    )
    # 提交由 get_db 依赖在请求正常结束时统一完成
    return ReceiveOut(
        ref_no=ref_no,
        status=ref.status,
        gross_amount=float(gross),
        splits=[
            SplitOut(payee_type=s.payee_type, payee_id=payee_of[s.payee_type], amount=float(s.amount))
            for s in splits
        ],
    )


# ---- 七节点积分链 / 个人服务信用账户 ----
class NodeCompleteOut(BaseModel):
    ref_no: str
    node: str
    points: int
    earned: float
    account_points: int
    account_balance: float


class LedgerItem(BaseModel):
    node: str
    points: int
    earned: float


class AccountOut(BaseModel):
    user_id: str
    points: int
    balance: float
    ledger: list[LedgerItem]


@router.post(
    "/referrals/{ref_no}/nodes/{node}/complete", response_model=NodeCompleteOut
)
def complete_node(
    ref_no: str,
    node: str,
    user: AuthUser = Depends(require_cap("referral:initiate", "referral:receive")),
    db: Session = Depends(get_db),
) -> NodeCompleteOut:
    """完成转诊闭环的一个节点 → 记分入个人服务信用账户（三源折算落账，不按月清零）。"""
    if node not in NODE_POINTS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"未知节点: {node}")

    ref = db.scalar(
        select(Referral).where(Referral.ref_no == ref_no, Referral.is_deleted.is_(False))
    )
    if ref is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="转诊单不存在")
    if not (has_global_scope(user) or ref.dept_code in user.scopes):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="无权操作该转诊单")

    nrow = db.scalar(
        select(ReferralNode).where(
            ReferralNode.ref_no == ref_no, ReferralNode.node == node
        )
    )
    if nrow is not None and nrow.done_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="该节点已完成")

    pts = NODE_POINTS[node]
    money = POINT_UNIT * pts
    # 三源折算（演示口径）：DRG 40% / 绩效 40% / 结余 20%
    drg = (money * Decimal("0.4")).quantize(Decimal("0.01"))
    perf = (money * Decimal("0.4")).quantize(Decimal("0.01"))
    surplus = money - drg - perf

    if nrow is None:
        nrow = ReferralNode(
            ref_no=ref_no, node=node, seq=list(NODE_POINTS).index(node) + 1
        )
        db.add(nrow)
    nrow.done_at = datetime.now(timezone.utc)
    nrow.operator = user.user_id

    db.add(
        CreditLedger(
            user_id=user.user_id, ref_no=ref_no, node=node, points=pts,
            drg_amt=drg, perf_amt=perf, surplus_amt=surplus,
        )
    )

    acct = db.get(CreditAccount, user.user_id)
    if acct is None:
        acct = CreditAccount(user_id=user.user_id, balance=Decimal("0"), points=0)
        db.add(acct)
    acct.points += pts
    acct.balance += money

    audit_action(
        user, action="complete_referral_node", scenario=settings.scenario_id,
        patient_id=ref.patient_id, target=f"{ref_no}:{node}",
    )
    db.flush()
    return NodeCompleteOut(
        ref_no=ref_no, node=node, points=pts, earned=float(money),
        account_points=acct.points, account_balance=float(acct.balance),
    )


@router.get("/credit/account", response_model=AccountOut)
def my_credit_account(
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AccountOut:
    """查看本人服务信用账户：累计积分、可兑现金额、明细流水。"""
    acct = db.get(CreditAccount, user.user_id)
    rows = db.scalars(
        select(CreditLedger).where(CreditLedger.user_id == user.user_id)
    ).all()
    audit_action(
        user, action="view_credit_account", scenario=settings.scenario_id,
        extra={"entries": len(rows)},
    )
    return AccountOut(
        user_id=user.user_id,
        points=acct.points if acct else 0,
        balance=float(acct.balance) if acct else 0.0,
        ledger=[
            LedgerItem(
                node=r.node,
                points=r.points,
                earned=float(r.drg_amt + r.perf_amt + r.surplus_amt),
            )
            for r in rows
        ],
    )


class NodeStatusOut(BaseModel):
    node: str
    points: int
    done: bool


@router.get("/referrals/{ref_no}/nodes", response_model=list[NodeStatusOut])
def list_nodes(
    ref_no: str,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[NodeStatusOut]:
    """某转诊单的七节点完成情况（按固定顺序返回）。"""
    ref = db.scalar(
        select(Referral).where(Referral.ref_no == ref_no, Referral.is_deleted.is_(False))
    )
    if ref is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="转诊单不存在")
    is_patient_owner = bool(user.patient_id) and ref.patient_id == user.patient_id
    if not (has_global_scope(user) or ref.dept_code in user.scopes or is_patient_owner):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="无权查看该转诊单")
    done = {
        r.node
        for r in db.scalars(
            select(ReferralNode).where(
                ReferralNode.ref_no == ref_no, ReferralNode.done_at.is_not(None)
            )
        ).all()
    }
    return [
        NodeStatusOut(node=n, points=p, done=(n in done)) for n, p in NODE_POINTS.items()
    ]
