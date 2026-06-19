"""家庭病床 集成测试（连真实 PostgreSQL；依赖 seed_external.py 灌入 P-1003 体征）。

验证：建床/准入(cap)/列表(scope)/体征监测(复用platform_iot)/任务/出院结算(复用platform_clearing)。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, text

from app.db import SessionFactory
from app.main import app
from app.models import Bed, BedMessage, CareTask

client = TestClient(app)


def _hdr(caps: str = "homebed:manage") -> dict[str, str]:
    return {"X-User-Id": "u1", "X-User-Roles": "doctor", "X-User-Scopes": "card", "X-User-Caps": caps}


def _clean(db) -> None:
    db.execute(delete(BedMessage).where(BedMessage.bed_no.in_(["HB-T1", "HB-T2"])))
    db.execute(delete(CareTask).where(CareTask.bed_no.in_(["HB-T1", "HB-T2"])))
    db.execute(delete(Bed).where(Bed.bed_no.in_(["HB-T1", "HB-T2"])))
    db.execute(text("DELETE FROM platform_clearing.income_split WHERE event_id IN (SELECT event_id FROM platform_clearing.income_event WHERE service_type='homebed_care' AND patient_id='P-1003')"))
    db.execute(text("DELETE FROM platform_clearing.income_event WHERE service_type='homebed_care' AND patient_id='P-1003'"))


@pytest.fixture(scope="module", autouse=True)
def seed():
    db = SessionFactory()
    _clean(db)
    db.execute(text("""INSERT INTO platform_clearing.service_rate_card(scenario_code,service_type,applies_org_tier,applies_title_rank,unit_price,individual_ratio,dept_ratio,org_ratio,platform_ratio,status)
                       SELECT 'scenario-002','homebed_care','any',0,80.00,0.60,0.20,0.10,0.10,'active'
                       WHERE NOT EXISTS(SELECT 1 FROM platform_clearing.service_rate_card WHERE service_type='homebed_care')"""))
    db.execute(text("INSERT INTO scenario_homebed.bed(bed_no,patient_id,status,care_level,admit_date,org_id,dept_code) VALUES('HB-T1','P-1003','admitted','一级护理', CURRENT_DATE - 3, 'wzcvh','card')"))
    db.execute(text("INSERT INTO scenario_homebed.bed(bed_no,patient_id,status,care_level,org_id,dept_code) VALUES('HB-T2','P-1003','reviewing','二级护理','wzcvh','card')"))
    db.commit()
    db.close()
    yield
    db = SessionFactory()
    _clean(db)
    db.commit()
    db.close()


def test_create_requires_cap():
    r = client.post("/api/scenario-002/beds", headers=_hdr(caps=""), json={"patient_id": "P-1003"})
    assert r.status_code == 403


def test_list_beds_scoped():
    r = client.get("/api/scenario-002/beds", headers=_hdr())
    assert r.status_code == 200
    assert any(b["bed_no"] == "HB-T1" for b in r.json())


def test_review_admits():
    r = client.post("/api/scenario-002/beds/HB-T2/review", headers=_hdr(), json={"approved": True})
    assert r.status_code == 200 and r.json()["status"] == "admitted"


def test_monitor_uses_platform_iot():
    r = client.get("/api/scenario-002/beds/HB-T1/monitor", headers=_hdr())
    assert r.status_code == 200
    body = r.json()
    assert "spo2" in {v["metric"] for v in body["latest"]}
    assert body["alert_count"] >= 3  # P-1003 有血氧/血压/心率异常


def test_care_tasks():
    add = client.post("/api/scenario-002/beds/HB-T1/tasks", headers=_hdr(), json={"type": "查房", "content": "评估血氧"})
    assert add.status_code == 201
    tid = add.json()["id"]
    assert client.post(f"/api/scenario-002/tasks/{tid}/done", headers=_hdr()).json()["status"] == "done"


def test_dashboard():
    r = client.get("/api/scenario-002/dashboard", headers=_hdr())
    assert r.status_code == 200
    assert r.json()["admitted"] >= 1  # HB-T1 在床


def test_quality():
    r = client.get("/api/scenario-002/quality", headers=_hdr())
    assert r.status_code == 200
    assert r.json()["abnormal_total"] >= 3  # P-1003 体征异常


def test_remote_messages():
    add = client.post("/api/scenario-002/beds/HB-T1/messages", headers=_hdr(), json={"content": "测试问诊消息"})
    assert add.status_code == 201 and add.json()["sender_role"] == "doctor"
    msgs = client.get("/api/scenario-002/beds/HB-T1/messages", headers=_hdr()).json()
    assert any(m["content"] == "测试问诊消息" for m in msgs)


def test_discharge_bills_via_clearing():
    r = client.post("/api/scenario-002/beds/HB-T1/discharge", headers=_hdr())
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "discharged" and body["days"] == 3
    assert body["gross_amount"] == 240.0  # 3天 × 80
    by = {s["payee_type"]: s["amount"] for s in body["splits"]}
    assert by["individual"] == 144.0  # 240 × 0.6
