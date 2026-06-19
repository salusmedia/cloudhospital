"""在线复诊 集成测试（连真实 PostgreSQL；依赖 seed_external.py 灌入 TC-001/002）。

验证：候诊队列(scope)/接诊(cap)/AI审方/结束计酬(复用 platform_clearing)/越权与状态机。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, text

from app.db import SessionFactory
from app.main import app
from app.models import Consult, ConsultRx

client = TestClient(app)
NO = "TC-T1"


def _hdr(caps: str = "teleconsult:treat") -> dict[str, str]:
    return {"X-User-Id": "u1", "X-User-Roles": "doctor", "X-User-Scopes": "card", "X-User-Caps": caps}


@pytest.fixture(scope="module", autouse=True)
def seed():
    db = SessionFactory()
    db.execute(delete(ConsultRx).where(ConsultRx.consult_no == NO))
    db.execute(delete(Consult).where(Consult.consult_no == NO))
    db.execute(
        text("DELETE FROM platform_clearing.income_split WHERE event_id IN (SELECT event_id FROM platform_clearing.income_event WHERE service_type='online_consult' AND patient_id='P-T1')")
    )
    db.execute(text("DELETE FROM platform_clearing.income_event WHERE service_type='online_consult' AND patient_id='P-T1'"))
    db.execute(
        text("""INSERT INTO platform_clearing.service_rate_card(scenario_code,service_type,applies_org_tier,applies_title_rank,unit_price,individual_ratio,dept_ratio,org_ratio,platform_ratio,status)
                SELECT 'scenario-006','online_consult','any',0,30.00,0.70,0.10,0.10,0.10,'active'
                WHERE NOT EXISTS(SELECT 1 FROM platform_clearing.service_rate_card WHERE service_type='online_consult')""")
    )
    db.add(Consult(consult_no=NO, patient_id="P-T1", status="waiting", chief_complaint="复诊", ai_triage="low", org_id="wzcvh", dept_code="card"))
    db.commit()
    db.close()
    yield
    db = SessionFactory()
    db.execute(delete(ConsultRx).where(ConsultRx.consult_no == NO))
    db.execute(delete(Consult).where(Consult.consult_no == NO))
    db.commit()
    db.close()


def test_queue_scoped():
    r = client.get("/api/scenario-006/consults?status=waiting", headers=_hdr())
    assert r.status_code == 200
    assert any(c["consult_no"] == NO for c in r.json())


def test_accept_requires_cap():
    r = client.post(f"/api/scenario-006/consults/{NO}/accept", headers=_hdr(caps=""))
    assert r.status_code == 403


def test_full_flow():
    assert client.post(f"/api/scenario-006/consults/{NO}/accept", headers=_hdr()).status_code == 200
    # AI 审方：含 NSAID 触发预警
    warn = client.post(f"/api/scenario-006/consults/{NO}/prescribe", headers=_hdr(), json={"drug_name": "布洛芬缓释胶囊"}).json()
    assert warn["ai_review"] == "warn"
    ok = client.post(f"/api/scenario-006/consults/{NO}/prescribe", headers=_hdr(), json={"drug_name": "氨氯地平 5mg", "usage": "qd"}).json()
    assert ok["ai_review"] == "passed"
    # 结束计酬，复用 platform_clearing：30 → 个人21/科室3/机构3/平台3
    fin = client.post(f"/api/scenario-006/consults/{NO}/finish", headers=_hdr()).json()
    assert fin["status"] == "finished" and fin["gross_amount"] == 30.0
    by = {s["payee_type"]: s["amount"] for s in fin["splits"]}
    assert by["individual"] == 21.0 and by["dept"] == 3.0 and by["org"] == 3.0 and by["platform"] == 3.0


def test_finish_twice_conflict():
    r = client.post(f"/api/scenario-006/consults/{NO}/finish", headers=_hdr())
    assert r.status_code == 409
