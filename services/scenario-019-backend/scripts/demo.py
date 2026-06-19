"""手动演示：建转诊单 → 调"接收"接口 → 看真实数据库里的分账。

跑法（需先起好 compose.dev.yml 的数据库）：
    cd services/scenario-019-backend
    uv run python scripts/demo.py
自带清理，跑完不留垃圾数据。
"""

from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db import SessionFactory
from app.main import app
from app.models import IncomeEvent, IncomeSplit, Referral, ServiceRateCard

DOC = "demo_doc"
REF = "DEMO-001"


def cleanup(db) -> None:
    ev_ids = select(IncomeEvent.event_id).where(IncomeEvent.performer_user_id == DOC)
    db.execute(delete(IncomeSplit).where(IncomeSplit.event_id.in_(ev_ids)))
    db.execute(delete(IncomeEvent).where(IncomeEvent.performer_user_id == DOC))
    db.execute(delete(Referral).where(Referral.ref_no == REF))
    db.execute(
        delete(ServiceRateCard).where(
            ServiceRateCard.scenario_code == "scenario-019",
            ServiceRateCard.service_type == "referral_receive",
        )
    )
    db.commit()


def main() -> None:
    db = SessionFactory()
    cleanup(db)
    db.add(
        ServiceRateCard(
            scenario_code="scenario-019", service_type="referral_receive",
            applies_org_tier="any", applies_title_rank=0,
            unit_price=Decimal("50.00"),
            individual_ratio=Decimal("0.60"), dept_ratio=Decimal("0.20"),
            org_ratio=Decimal("0.20"), platform_ratio=Decimal("0.00"),
            floor_price=None, cap_price=None, status="active",
        )
    )
    db.add(
        Referral(
            ref_no=REF, patient_id="p_demo", source_org="community-wt",
            source_doctor="liming", target_org="wzcvh", target_doctor=DOC,
            ref_type="上转", risk_level="黄", status="applying",
            org_id="wzcvh", dept_code="card",
        )
    )
    db.commit()
    db.close()

    client = TestClient(app)
    hdr = {
        "X-User-Id": DOC, "X-User-Name": "%E7%8E%8B%E5%8C%BB%E7%94%9F",
        "X-User-Roles": "doctor", "X-User-Scopes": "card",
        "X-User-Caps": "referral:receive",
    }
    print("① 接收转诊（POST /referrals/DEMO-001/receive）→ 接口返回：")
    resp = client.post("/api/scenario-019/referrals/DEMO-001/receive", headers=hdr)
    print("   状态码:", resp.status_code, "| 单据状态:", resp.json()["status"])
    print("   毛收入: ¥", resp.json()["gross_amount"])

    db = SessionFactory()
    print("\n② 直接查数据库 platform_clearing.income_split —— 真实落库的 4 行分账：")
    rows = db.scalars(
        select(IncomeSplit)
        .join(IncomeEvent, IncomeSplit.event_id == IncomeEvent.event_id)
        .where(IncomeEvent.performer_user_id == DOC)
    ).all()
    for s in rows:
        print(f"   {s.payee_type:<11} 收款方={s.payee_id:<12} 金额 ¥{s.amount}")
    print("   合计 ¥", sum(s.amount for s in rows))
    cleanup(db)
    db.close()
    print("\n③ 已清理演示数据。")


if __name__ == "__main__":
    main()
