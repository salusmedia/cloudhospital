"""管理端（医共体运营驾驶舱）接口：统计、机构分账、规则配置、异常预警处置。

注意：本视图是全局聚合（跨科室/机构），生产应限定 regulator/org_admin 角色；
演示期为便于单账号体验，仅校验登录。聚合不经 scope_filter（管理者视角）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.models import ReferralAlert
from py_common import AuthUser, audit_action, get_current_user

router = APIRouter(prefix=f"{settings.api_prefix}/admin", tags=["scenario-019-admin"])


class Kpi(BaseModel):
    total: int
    up: int
    down: int
    flat: int
    emergency: int
    received_rate: float
    mutual_recognition_rate: float


class OrgRank(BaseModel):
    org_id: str
    org_name: str | None
    inbound: int


class Dashboard(BaseModel):
    kpi: Kpi
    type_distribution: dict[str, int]
    org_ranking: list[OrgRank]


@router.get("/dashboard", response_model=Dashboard)
def dashboard(user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> Dashboard:
    base = "FROM scenario_referral.referral WHERE is_deleted=false"
    total = db.scalar(text(f"SELECT count(*) {base}")) or 0
    by_type: dict[str, int] = {
        row[0]: row[1] for row in db.execute(text(f"SELECT type, count(*) {base} GROUP BY type")).all()
    }
    received = db.scalar(text(f"SELECT count(*) {base} AND status='received'")) or 0
    pkg_total = db.scalar(text("SELECT count(*) FROM scenario_referral.referral_package")) or 0
    pkg_mr = db.scalar(text("SELECT count(*) FROM scenario_referral.referral_package WHERE mutual_recognition")) or 0
    ranking = db.execute(
        text("""
          SELECT r.target_org AS org_id, o.name AS org_name, count(*) AS inbound
          FROM scenario_referral.referral r
          LEFT JOIN platform_identity.organization o ON o.org_id=r.target_org
          WHERE r.is_deleted=false AND r.target_org IS NOT NULL
          GROUP BY r.target_org,o.name ORDER BY inbound DESC LIMIT 5
        """)
    ).mappings().all()
    audit_action(user, action="view_admin_dashboard", scenario=settings.scenario_id)
    return Dashboard(
        kpi=Kpi(
            total=total, up=by_type.get("up", 0), down=by_type.get("down", 0),
            flat=by_type.get("flat", 0), emergency=by_type.get("emergency", 0),
            received_rate=round(received / total, 3) if total else 0.0,
            mutual_recognition_rate=round(pkg_mr / pkg_total, 3) if pkg_total else 0.0,
        ),
        type_distribution={k: v for k, v in by_type.items()},
        org_ranking=[OrgRank(org_id=x["org_id"], org_name=x["org_name"], inbound=int(x["inbound"])) for x in ranking],
    )


class RulesOut(BaseModel):
    risk_layers: list[dict]
    time_limits: list[dict]
    mutual_recognition: list[dict]


@router.get("/rules", response_model=RulesOut)
def rules(user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> RulesOut:
    """规则配置：病情分层/时限为运营策略（演示内置）；互认目录来自 platform_dict。"""
    catalog = db.execute(
        text("SELECT category,item_name,valid_days,recognize_scope,status FROM platform_dict.mutual_recognition_catalog ORDER BY category,item_name")
    ).mappings().all()
    return RulesOut(
        risk_layers=[
            {"level": "红色 · 急危重症直达", "desc": "急性心梗、脑卒中、严重创伤等，绿色通道15分钟响应"},
            {"level": "黄色 · 县域/市级上转", "desc": "慢病加重、专科需进一步检查，2小时确认"},
            {"level": "绿色 · 基层处理", "desc": "常见病、慢病稳定期、康复期、健康管理"},
        ],
        time_limits=[
            {"scene": "急诊绿色通道", "limit": "15分钟", "warn": "10分钟"},
            {"scene": "普通上转确认", "limit": "2小时", "warn": "1.5小时"},
            {"scene": "下转接续", "limit": "24小时", "warn": "20小时"},
            {"scene": "MDT响应", "limit": "48小时", "warn": "36小时"},
        ],
        mutual_recognition=[dict(x) for x in catalog],
    )


class SettlementOut(BaseModel):
    measures: list[dict]
    org_settlements: list[dict]


@router.get("/settlements", response_model=SettlementOut)
def settlements(user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> SettlementOut:
    """绩效分账：协同服务计量（按转诊量折算）+ 机构分账明细。"""
    total = db.scalar(text("SELECT count(*) FROM scenario_referral.referral WHERE is_deleted=false")) or 0
    up = db.scalar(text("SELECT count(*) FROM scenario_referral.referral WHERE is_deleted=false AND type='up'")) or 0
    down = db.scalar(text("SELECT count(*) FROM scenario_referral.referral WHERE is_deleted=false AND type='down'")) or 0
    measures = [
        {"name": "首诊识别服务", "qty": total, "unit": 20, "subtotal": total * 20},
        {"name": "上转协同服务", "qty": up, "unit": 50, "subtotal": up * 50},
        {"name": "下转康复服务", "qty": down, "unit": 40, "subtotal": down * 40},
    ]
    org_settlements = [
        dict(x) for x in db.execute(
            text("SELECT org_id,period,service_amount,quality_bonus,actual_alloc FROM scenario_referral.org_settlement ORDER BY period DESC,org_id")
        ).mappings().all()
    ]
    return SettlementOut(measures=measures, org_settlements=org_settlements)


class AlertOut(BaseModel):
    id: str
    ref_no: str | None
    level: str
    category: str
    title: str
    detail: str | None
    status: str


@router.get("/alerts", response_model=list[AlertOut])
def alerts(user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> list[AlertOut]:
    rows = db.scalars(select(ReferralAlert).order_by(ReferralAlert.level, ReferralAlert.created_at.desc())).all()
    return [AlertOut(id=str(a.id), ref_no=a.ref_no, level=a.level, category=a.category, title=a.title, detail=a.detail, status=a.status) for a in rows]


@router.post("/alerts/{alert_id}/handle")
def handle_alert(alert_id: str, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, str]:
    from datetime import datetime, timezone

    a = db.get(ReferralAlert, alert_id)
    if a is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="预警不存在")
    a.status = "handled"
    a.handled_by = user.user_id
    a.handled_at = datetime.now(timezone.utc)
    audit_action(user, action="handle_alert", scenario=settings.scenario_id, target=str(alert_id))
    db.flush()
    return {"id": alert_id, "status": "handled"}
