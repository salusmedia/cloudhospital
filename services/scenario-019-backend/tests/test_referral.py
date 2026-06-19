"""转诊场景集成测试：连真实 PostgreSQL（compose.dev.yml 的 hospital 库）。

验证三件套端到端：
- scope_filter：心内科医生只看到本科室转诊单。
- require_cap：没有 referral:receive 能力 → 403。
- split_income：接收转诊 → 收入 4 方分账落库，加总=毛收入。

测试自带种子数据并在结束后清理（ref_no 前缀 TST-，用户 test_card_doc）。
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db import SessionFactory
from app.main import app
from app.models import IncomeEvent, IncomeSplit, Referral, ServiceRateCard

client = TestClient(app)

ORG = "wzcvh"
DOC = "test_card_doc"


def _hdr(scopes: str, caps: str) -> dict[str, str]:
    """模拟网关注入的可信身份头（X-User-*）。"""
    return {
        "X-User-Id": DOC,
        "X-User-Name": "%E7%8E%8B%E5%8C%BB%E7%94%9F",  # 王医生（URL-encode）
        "X-User-Roles": "doctor",
        "X-User-Scopes": scopes,
        "X-User-Caps": caps,
    }


def _cleanup(db) -> None:
    ev_ids = select(IncomeEvent.event_id).where(IncomeEvent.performer_user_id == DOC)
    db.execute(delete(IncomeSplit).where(IncomeSplit.event_id.in_(ev_ids)))
    db.execute(delete(IncomeEvent).where(IncomeEvent.performer_user_id == DOC))
    db.execute(delete(Referral).where(Referral.ref_no.like("TST-%")))
    db.execute(
        delete(ServiceRateCard).where(
            ServiceRateCard.scenario_code == "scenario-019",
            ServiceRateCard.service_type == "referral_receive",
        )
    )
    db.commit()


@pytest.fixture(scope="module", autouse=True)
def seed():
    db = SessionFactory()
    _cleanup(db)
    db.add(
        ServiceRateCard(
            scenario_code="scenario-019",
            service_type="referral_receive",
            applies_org_tier="any",
            applies_title_rank=0,
            unit_price=Decimal("50.00"),
            individual_ratio=Decimal("0.60"),
            dept_ratio=Decimal("0.20"),
            org_ratio=Decimal("0.20"),
            platform_ratio=Decimal("0.00"),
            floor_price=None,
            cap_price=None,
            status="active",
        )
    )
    for ref_no, dept in (("TST-CARD", "card"), ("TST-ENDO", "endo")):
        db.add(
            Referral(
                ref_no=ref_no,
                patient_id="p_demo",
                source_org="community-wt",
                source_doctor="liming",
                target_org=ORG,
                target_doctor=DOC,
                ref_type="上转",
                risk_level="黄",
                status="applying",
                org_id=ORG,
                dept_code=dept,
            )
        )
    db.commit()
    db.close()
    yield
    db = SessionFactory()
    _cleanup(db)
    db.close()


def test_list_referrals_scoped_to_dept():
    # 心内科医生只看到本科室（card），看不到 endo
    r = client.get("/api/scenario-019/referrals", headers=_hdr("card", ""))
    assert r.status_code == 200
    ref_nos = {x["ref_no"] for x in r.json()}
    assert "TST-CARD" in ref_nos
    assert "TST-ENDO" not in ref_nos


def test_receive_denied_without_cap():
    # 有数据权限但没有 referral:receive 能力 → 403（require_cap 在进入业务前就挡掉）
    r = client.post("/api/scenario-019/referrals/TST-CARD/receive", headers=_hdr("card", ""))
    assert r.status_code == 403


def test_receive_ok_and_split_income():
    # 有能力 + 有数据权限 → 接收成功，收入 4 方分账，加总=毛收入
    r = client.post(
        "/api/scenario-019/referrals/TST-CARD/receive",
        headers=_hdr("card", "referral:receive"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "received"
    assert body["gross_amount"] == 50.0
    by = {s["payee_type"]: s["amount"] for s in body["splits"]}
    assert by["individual"] == 30.0  # 50 * 0.6
    assert by["dept"] == 10.0
    assert by["org"] == 10.0
    assert sum(by.values()) == 50.0

    # 确认真落库了
    db = SessionFactory()
    ev = db.scalar(select(IncomeEvent).where(IncomeEvent.performer_user_id == DOC))
    assert ev is not None and float(ev.gross_amount) == 50.0
    db.close()
