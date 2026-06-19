"""转诊临床流程接口（患者端 + 医生端）。

详情/时间轴/医保测算/资料互认/知情同意/五要素/退回/智能推荐接收机构/下转康复方案。
跨 schema 只读用原始 SQL（platform_identity/platform_insurance/platform_dict/platform_appointment）；
本场景表的写入用 ORM。所有接口先校验登录 + 对该转诊单的科室数据权限。
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.models import (
    DownwardPlan,
    DownwardPlanDrug,
    Referral,
    ReferralConsent,
    ReferralTrack,
)
from py_common import AuthUser, audit_action, get_current_user, has_global_scope, require_cap

router = APIRouter(prefix=settings.api_prefix, tags=["scenario-019-clinical"])


def _load_ref(db: Session, ref_no: str, user: AuthUser) -> Referral:
    ref = db.scalar(
        select(Referral).where(Referral.ref_no == ref_no, Referral.is_deleted.is_(False))
    )
    if ref is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="转诊单不存在")
    is_patient_owner = bool(user.patient_id) and ref.patient_id == user.patient_id
    if not (has_global_scope(user) or ref.dept_code in user.scopes or is_patient_owner):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="无权访问该转诊单")
    return ref


def _org_name(db: Session, org_id: str | None) -> str | None:
    if not org_id:
        return None
    return db.scalar(
        text("SELECT name FROM platform_identity.organization WHERE org_id=:o"), {"o": org_id}
    )


def _staff_name(db: Session, user_id: str | None) -> str | None:
    if not user_id:
        return None
    return db.scalar(
        text("SELECT name FROM platform_identity.staff_profile WHERE user_id=:u"), {"u": user_id}
    )


# ---------- 详情 ----------
class ReferralDetail(BaseModel):
    ref_no: str
    patient_id: str
    type: str
    risk_level: str
    status: str
    dept_code: str
    source_org: str | None
    source_org_name: str | None
    source_doctor: str | None
    source_doctor_name: str | None
    target_org: str | None
    target_org_name: str | None
    target_doctor: str | None
    target_doctor_name: str | None
    appointment_slot: str | None


@router.get("/referrals/{ref_no}/detail", response_model=ReferralDetail)
def get_detail(ref_no: str, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> ReferralDetail:
    r = _load_ref(db, ref_no, user)
    audit_action(user, action="get_referral_detail", scenario=settings.scenario_id, patient_id=r.patient_id, target=ref_no)
    return ReferralDetail(
        ref_no=r.ref_no, patient_id=r.patient_id, type=r.ref_type, risk_level=r.risk_level,
        status=r.status, dept_code=r.dept_code,
        source_org=r.source_org, source_org_name=_org_name(db, r.source_org),
        source_doctor=r.source_doctor, source_doctor_name=_staff_name(db, r.source_doctor),
        target_org=r.target_org, target_org_name=_org_name(db, r.target_org),
        target_doctor=r.target_doctor, target_doctor_name=_staff_name(db, r.target_doctor),
        appointment_slot=r.appointment_slot,
    )


# ---------- 时间轴 ----------
class TrackItem(BaseModel):
    seq: int
    title: str
    detail: str | None
    occurred_at: datetime | None


@router.get("/referrals/{ref_no}/track", response_model=list[TrackItem])
def get_track(ref_no: str, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> list[TrackItem]:
    _load_ref(db, ref_no, user)
    rows = db.scalars(
        select(ReferralTrack).where(ReferralTrack.ref_no == ref_no).order_by(ReferralTrack.seq)
    ).all()
    return [TrackItem(seq=t.seq, title=t.title, detail=t.detail, occurred_at=t.occurred_at) for t in rows]


# ---------- 医保测算 ----------
class InsuranceEstimate(BaseModel):
    insurance_type: str | None
    filed: bool | None
    total: float
    deductible: float
    reimburse_ratio: float
    reimbursed: float
    self_pay: float
    annual_reimbursed: float | None
    cap_line: float | None
    saved_vs_unfiled: float  # 因已备案相比未备案节省


@router.get("/referrals/{ref_no}/insurance", response_model=InsuranceEstimate)
def get_insurance(
    ref_no: str,
    total: float = Query(default=8500, ge=0),
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InsuranceEstimate:
    """医保测算（读 platform_insurance 的参保信息 + 报销规则）。"""
    r = _load_ref(db, ref_no, user)
    ins = db.execute(
        text("SELECT insurance_type,filed,annual_reimbursed,cap_line FROM platform_insurance.patient_insurance WHERE patient_id=:p"),
        {"p": r.patient_id},
    ).mappings().first()
    ins_type = ins["insurance_type"] if ins else "城乡居民"
    filed = bool(ins["filed"]) if ins else False

    def rule(is_filed: bool) -> dict | None:
        row = db.execute(
            text("""SELECT deductible,reimburse_ratio,cap_line FROM platform_insurance.insurance_policy_rule
                    WHERE referral_type=:t AND insurance_type=:i AND filed=:f"""),
            {"t": r.ref_type, "i": ins_type, "f": is_filed},
        ).mappings().first()
        return dict(row) if row else None

    rule_now = rule(filed) or rule(True) or {"deductible": 800, "reimburse_ratio": 0.85, "cap_line": 150000}
    ded = float(rule_now["deductible"])
    ratio = float(rule_now["reimburse_ratio"])
    reimbursed = max(total - ded, 0) * ratio
    self_pay = total - reimbursed

    saved = 0.0
    r_unfiled = rule(False)
    if filed and r_unfiled:
        reimb_unfiled = max(total - float(r_unfiled["deductible"]), 0) * float(r_unfiled["reimburse_ratio"])
        saved = round(reimbursed - reimb_unfiled, 2)

    audit_action(user, action="estimate_insurance", scenario=settings.scenario_id, patient_id=r.patient_id, target=ref_no)
    return InsuranceEstimate(
        insurance_type=ins_type, filed=filed, total=total, deductible=ded,
        reimburse_ratio=ratio, reimbursed=round(reimbursed, 2), self_pay=round(self_pay, 2),
        annual_reimbursed=float(ins["annual_reimbursed"]) if ins else None,
        cap_line=float(ins["cap_line"]) if ins else None,
        saved_vs_unfiled=saved,
    )


# ---------- 资料互认 ----------
class MaterialItem(BaseModel):
    doc_type: str
    source_report_id: str | None
    mutual_recognition: bool
    valid_days: int | None
    recognize_scope: str | None
    conclusion: str | None  # 来自真实健康档案 platform_archive.report


@router.get("/referrals/{ref_no}/materials", response_model=list[MaterialItem])
def get_materials(ref_no: str, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> list[MaterialItem]:
    """资料包 + 检查互认目录(platform_dict) + 真实报告结论(platform_archive)。"""
    _load_ref(db, ref_no, user)
    rows = db.execute(
        text("""
          SELECT p.doc_type, p.source_report_id, p.mutual_recognition,
                 c.valid_days, c.recognize_scope, r.conclusion
          FROM scenario_referral.referral_package p
          LEFT JOIN platform_dict.mutual_recognition_catalog c ON c.item_name = p.doc_type
          LEFT JOIN platform_archive.report r ON r.report_id = p.source_report_id
          WHERE p.ref_no = :r
          ORDER BY p.doc_type
        """),
        {"r": ref_no},
    ).mappings().all()
    return [
        MaterialItem(
            doc_type=x["doc_type"], source_report_id=x["source_report_id"],
            mutual_recognition=bool(x["mutual_recognition"]),
            valid_days=x["valid_days"], recognize_scope=x["recognize_scope"],
            conclusion=x["conclusion"],
        )
        for x in rows
    ]


# ---------- 知情同意 ----------
class ConsentItem(BaseModel):
    doc_name: str
    seq: int
    signed: bool
    signed_at: datetime | None


@router.get("/referrals/{ref_no}/consents", response_model=list[ConsentItem])
def get_consents(ref_no: str, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> list[ConsentItem]:
    _load_ref(db, ref_no, user)
    rows = db.scalars(
        select(ReferralConsent).where(ReferralConsent.ref_no == ref_no).order_by(ReferralConsent.seq)
    ).all()
    return [ConsentItem(doc_name=c.doc_name, seq=c.seq, signed=c.signed, signed_at=c.signed_at) for c in rows]


@router.post("/referrals/{ref_no}/consents/{doc_name}/sign", response_model=ConsentItem)
def sign_consent(
    ref_no: str, doc_name: str,
    user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db),
) -> ConsentItem:
    """电子签署一份知情同意书（全程留痕）。"""
    _load_ref(db, ref_no, user)
    c = db.scalar(
        select(ReferralConsent).where(ReferralConsent.ref_no == ref_no, ReferralConsent.doc_name == doc_name)
    )
    if c is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="无此文件")
    c.signed = True
    c.signed_at = datetime.now(timezone.utc)
    c.signer = user.user_id
    audit_action(user, action="sign_consent", scenario=settings.scenario_id, target=f"{ref_no}:{doc_name}")
    db.flush()
    return ConsentItem(doc_name=c.doc_name, seq=c.seq, signed=c.signed, signed_at=c.signed_at)


# ---------- 五要素 ----------
class CheckItem(BaseModel):
    item: str
    passed: bool


@router.get("/referrals/{ref_no}/checks", response_model=list[CheckItem])
def get_checks(ref_no: str, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> list[CheckItem]:
    _load_ref(db, ref_no, user)
    rows = db.execute(
        text("SELECT item,passed FROM scenario_referral.referral_check WHERE ref_no=:r ORDER BY item"),
        {"r": ref_no},
    ).mappings().all()
    return [CheckItem(item=x["item"], passed=bool(x["passed"])) for x in rows]


# ---------- 退回 ----------
class RejectIn(BaseModel):
    reason: str = "资料不完整"


@router.post("/referrals/{ref_no}/reject")
def reject_referral(
    ref_no: str, payload: RejectIn,
    user: AuthUser = Depends(require_cap("referral:receive")), db: Session = Depends(get_db),
) -> dict[str, str]:
    """接收方退回转诊（需能力 referral:receive）。状态置 rejected 并记时间轴。"""
    r = _load_ref(db, ref_no, user)
    if r.status not in ("applying",):
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"当前状态 {r.status} 不可退回")
    r.status = "rejected"
    _add_track(db, ref_no, "转诊被退回", payload.reason, user.user_id)
    audit_action(user, action="reject_referral", scenario=settings.scenario_id, patient_id=r.patient_id, target=ref_no)
    db.flush()
    return {"ref_no": ref_no, "status": r.status}


def _add_track(db: Session, ref_no: str, title: str, detail: str, operator: str) -> None:
    seq = (db.scalar(text("SELECT COALESCE(MAX(seq),0)+1 FROM scenario_referral.referral_track WHERE ref_no=:r"), {"r": ref_no})) or 1
    db.add(ReferralTrack(ref_no=ref_no, seq=int(seq), title=title, detail=detail, operator=operator))


# ---------- 智能推荐接收机构 ----------
# 机构到基层的距离（km）。生产来自卫健委地理数据；此处为演示静态值。
_DISTANCE_KM = {"wzcvh": 12, "wmu1": 18, "nhsc": 8, "wtsc": 3}


class RecommendItem(BaseModel):
    org_id: str
    org_name: str
    tier: str
    score: int
    available_slots: int
    distance_km: int | None
    specialty_advantage: bool
    next_slot: str | None
    reasons: list[str]


@router.get("/recommend", response_model=list[RecommendItem])
def recommend(
    dept: str = Query(...),
    type: str = Query(default="up"),
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RecommendItem]:
    """按科室智能推荐接收机构：综合机构等级、可用号源、距离、专科优势综合评分。"""
    rows = db.execute(
        text("""
          SELECT o.org_id, o.name, o.tier,
                 COALESCE(SUM(s.remaining),0) AS slots,
                 MIN(s.slot_time) FILTER (WHERE s.remaining>0) AS next_slot,
                 EXISTS(SELECT 1 FROM platform_identity.department d
                        WHERE d.org_id=o.org_id AND d.dept_code=:d) AS has_specialty
          FROM platform_identity.organization o
          LEFT JOIN platform_appointment.appointment_slot s
                 ON s.org_id=o.org_id AND s.dept_code=:d AND s.status='open'
          WHERE o.tier IN ('三级','二级')
          GROUP BY o.org_id,o.name,o.tier
        """),
        {"d": dept},
    ).mappings().all()
    out: list[RecommendItem] = []
    for x in rows:
        slots = int(x["slots"])
        dist = _DISTANCE_KM.get(x["org_id"])
        specialty = bool(x["has_specialty"])
        # 综合评分：等级 + 号源 + 距离(越近越高) + 专科优势 + 医保定点
        score = (40 if x["tier"] == "三级" else 25)
        score += min(slots, 10) * 3
        score += max(0, 20 - dist) if dist is not None else 0
        score += 12 if specialty else 0
        score += 10  # 医保定点
        reasons = [f"{x['tier']}医院", "医保定点·85%"]
        reasons.append("有号源·专家转诊号" if slots > 0 else "号源紧张")
        if dist is not None:
            reasons.append(f"距离{dist}km")
        if specialty:
            reasons.append("对口专科优势")
        out.append(RecommendItem(
            org_id=x["org_id"], org_name=x["name"], tier=x["tier"], score=min(score, 99),
            available_slots=slots, distance_km=dist, specialty_advantage=specialty,
            next_slot=str(x["next_slot"]) if x["next_slot"] else None, reasons=reasons,
        ))
    out.sort(key=lambda r: r.score, reverse=True)
    return out


# ---------- 患者端：我的转诊 ----------
class MyReferral(BaseModel):
    ref_no: str
    type: str
    risk_level: str
    status: str
    target_org_name: str | None


@router.get("/my/referrals", response_model=list[MyReferral])
def my_referrals(user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> list[MyReferral]:
    """患者端：查看本人的转诊单（按绑定的 patient_id）。"""
    if not user.patient_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="非患者身份")
    rows = db.scalars(
        select(Referral).where(Referral.patient_id == user.patient_id, Referral.is_deleted.is_(False))
    ).all()
    audit_action(user, action="patient_list_referrals", scenario=settings.scenario_id, patient_id=user.patient_id)
    return [
        MyReferral(
            ref_no=r.ref_no, type=r.ref_type, risk_level=r.risk_level, status=r.status,
            target_org_name=_org_name(db, r.target_org),
        )
        for r in rows
    ]


# ---------- 下转康复方案 ----------
class DrugIn(BaseModel):
    drug: str
    usage: str | None = None
    course: str | None = None


class DownwardIn(BaseModel):
    summary: str
    review_plan: str | None = None
    drugs: list[DrugIn] = []


class DownwardOut(BaseModel):
    ref_no: str
    summary: str | None
    review_plan: str | None
    status: str
    drugs: list[DrugIn]


@router.get("/referrals/{ref_no}/downward", response_model=DownwardOut | None)
def get_downward(ref_no: str, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> DownwardOut | None:
    _load_ref(db, ref_no, user)
    plan = db.scalar(select(DownwardPlan).where(DownwardPlan.ref_no == ref_no))
    if plan is None:
        return None
    drugs = db.scalars(select(DownwardPlanDrug).where(DownwardPlanDrug.plan_id == plan.id)).all()
    return DownwardOut(
        ref_no=ref_no, summary=plan.summary, review_plan=plan.review_plan, status=plan.status,
        drugs=[DrugIn(drug=d.drug, usage=d.usage, course=d.course) for d in drugs],
    )


@router.post("/referrals/{ref_no}/downward", response_model=DownwardOut)
def create_downward(
    ref_no: str, payload: DownwardIn,
    user: AuthUser = Depends(require_cap("referral:initiate", "referral:receive")), db: Session = Depends(get_db),
) -> DownwardOut:
    """下发下转康复方案（上级医院）。"""
    r = _load_ref(db, ref_no, user)
    if db.scalar(select(DownwardPlan).where(DownwardPlan.ref_no == ref_no)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="该单已有下转方案")
    plan = DownwardPlan(ref_no=ref_no, summary=payload.summary, review_plan=payload.review_plan, created_by=user.user_id)
    db.add(plan)
    db.flush()
    for d in payload.drugs:
        db.add(DownwardPlanDrug(plan_id=plan.id, drug=d.drug, usage=d.usage, course=d.course))
    r.ref_type = "down"
    _add_track(db, ref_no, "下转康复方案已下发", payload.summary[:80], user.user_id)
    audit_action(user, action="create_downward_plan", scenario=settings.scenario_id, patient_id=r.patient_id, target=ref_no)
    db.flush()
    return DownwardOut(ref_no=ref_no, summary=plan.summary, review_plan=plan.review_plan, status=plan.status, drugs=payload.drugs)
