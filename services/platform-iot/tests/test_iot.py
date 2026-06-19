"""体征监测 集成测试（连真实 PostgreSQL；依赖 seed_external.py 灌入 P-1003 体征与阈值）。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import SessionFactory
from app.main import app

client = TestClient(app)


def _staff() -> dict[str, str]:
    return {"X-User-Id": "u1", "X-User-Roles": "nurse", "X-User-Scopes": "card"}


def _patient(pid: str) -> dict[str, str]:
    return {"X-User-Id": "pt", "X-User-Roles": "resident", "X-User-Patient-Id": pid}


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    db = SessionFactory()
    db.execute(text("DELETE FROM platform_iot.vital_sign WHERE patient_id='P-TIOT'"))
    db.commit()
    db.close()


def test_record_flags_abnormal_by_threshold():
    low = client.post("/api/platform-iot/vitals", headers=_staff(), json={"patient_id": "P-TIOT", "metric": "spo2", "value_num": 85, "value_text": "85"})
    assert low.status_code == 201 and low.json()["abnormal_flag"] is True
    ok = client.post("/api/platform-iot/vitals", headers=_staff(), json={"patient_id": "P-TIOT", "metric": "spo2", "value_num": 97, "value_text": "97"})
    assert ok.json()["abnormal_flag"] is False


def test_seeded_alerts():
    r = client.get("/api/platform-iot/patients/P-1003/alerts", headers=_staff())
    assert r.status_code == 200
    metrics = {x["metric"] for x in r.json()}
    assert "spo2" in metrics  # 血氧89 触发预警


def test_latest_one_per_metric():
    r = client.get("/api/platform-iot/patients/P-1003/vitals/latest", headers=_staff())
    assert r.status_code == 200
    metrics = [x["metric"] for x in r.json()]
    assert len(metrics) == len(set(metrics))  # 每指标仅一条
    assert "spo2" in metrics


def test_patient_self_vs_other():
    assert client.get("/api/platform-iot/patients/P-1003/vitals", headers=_patient("P-1003")).status_code == 200
    assert client.get("/api/platform-iot/patients/P-1003/vitals", headers=_patient("P-9999")).status_code == 403


def test_requires_auth():
    assert client.get("/api/platform-iot/patients/P-1003/vitals").status_code == 401
