"""七节点积分链 / 个人服务信用账户 集成测试（连真实 PostgreSQL）。

- 完成节点 → 记分入信用账户（三源折算）。
- 同一节点重复完成 → 409。
- 查账户 → 累计积分/金额/流水正确。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db import SessionFactory
from app.main import app
from app.models import CreditAccount, CreditLedger, Referral, ReferralNode

client = TestClient(app)

DOC = "test_credit_doc"
REF = "TST-CR"


def _hdr(caps: str = "referral:initiate") -> dict[str, str]:
    return {
        "X-User-Id": DOC,
        "X-User-Name": "%E6%9D%8E%E5%8C%BB%E7%94%9F",
        "X-User-Roles": "doctor",
        "X-User-Scopes": "card",
        "X-User-Caps": caps,
    }


def _cleanup(db) -> None:
    db.execute(delete(CreditLedger).where(CreditLedger.user_id == DOC))
    db.execute(delete(CreditAccount).where(CreditAccount.user_id == DOC))
    db.execute(delete(ReferralNode).where(ReferralNode.ref_no == REF))
    db.execute(delete(Referral).where(Referral.ref_no == REF))
    db.commit()


@pytest.fixture(scope="module", autouse=True)
def seed():
    db = SessionFactory()
    _cleanup(db)
    db.add(
        Referral(
            ref_no=REF, patient_id="p_demo", source_org="community-wt",
            source_doctor="liming", target_org="wzcvh", target_doctor=DOC,
            ref_type="up", risk_level="yellow", status="applying",
            org_id="wzcvh", dept_code="card",
        )
    )
    db.commit()
    db.close()
    yield
    db = SessionFactory()
    _cleanup(db)
    db.close()


def test_complete_node_awards_points():
    r = client.post(f"/api/scenario-019/referrals/{REF}/nodes/first_visit/complete", headers=_hdr())
    assert r.status_code == 200
    body = r.json()
    assert body["points"] == 15
    assert body["earned"] == 30.0  # 15 分 × 2.0 元/分
    assert body["account_points"] == 15


def test_second_node_accumulates():
    r = client.post(f"/api/scenario-019/referrals/{REF}/nodes/accept/complete", headers=_hdr())
    assert r.status_code == 200
    assert r.json()["account_points"] == 53  # 15 + 38


def test_duplicate_node_is_conflict():
    r = client.post(f"/api/scenario-019/referrals/{REF}/nodes/first_visit/complete", headers=_hdr())
    assert r.status_code == 409


def test_unknown_node_is_400():
    r = client.post(f"/api/scenario-019/referrals/{REF}/nodes/nope/complete", headers=_hdr())
    assert r.status_code == 400


def test_node_without_cap_denied():
    r = client.post(f"/api/scenario-019/referrals/{REF}/nodes/apply/complete", headers=_hdr(caps=""))
    assert r.status_code == 403


def test_view_account():
    r = client.get("/api/scenario-019/credit/account", headers=_hdr())
    assert r.status_code == 200
    body = r.json()
    assert body["points"] == 53
    assert body["balance"] == 106.0  # 53 分 × 2.0
    nodes = {x["node"] for x in body["ledger"]}
    assert nodes == {"first_visit", "accept"}
