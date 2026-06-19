"""健康档案 集成测试（连真实 PostgreSQL，依赖 seed_external.py 已灌入 P-1001）。

验证：跨院汇聚概览/就诊/报告/处方读取；访问控制（患者本人 vs 他人 vs 临床角色 vs 未认证）。
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
PID = "P-1001"


def _staff() -> dict[str, str]:
    return {"X-User-Id": "u1", "X-User-Roles": "doctor", "X-User-Scopes": "card"}


def _patient(pid: str) -> dict[str, str]:
    return {"X-User-Id": "pt", "X-User-Roles": "resident", "X-User-Patient-Id": pid}


def test_summary_staff():
    r = client.get(f"/api/platform-archive/patients/{PID}/summary", headers=_staff())
    assert r.status_code == 200
    b = r.json()
    assert b["encounters"] == 2 and b["orgs"] == 2 and b["reports"] == 5 and b["diagnoses"] == 2


def test_encounters_and_reports():
    enc = client.get(f"/api/platform-archive/patients/{PID}/encounters", headers=_staff()).json()
    assert len(enc) == 2
    reps = client.get(f"/api/platform-archive/patients/{PID}/reports", headers=_staff()).json()
    assert len(reps) == 5
    assert any(x["item_name"] == "胸部CT平扫" for x in reps)


def test_prescriptions_with_items():
    rx = client.get(f"/api/platform-archive/patients/{PID}/prescriptions", headers=_staff()).json()
    assert len(rx) == 1
    assert len(rx[0]["items"]) == 2


def test_patient_self_allowed():
    r = client.get(f"/api/platform-archive/patients/{PID}/summary", headers=_patient(PID))
    assert r.status_code == 200


def test_other_patient_forbidden():
    r = client.get(f"/api/platform-archive/patients/{PID}/summary", headers=_patient("P-9999"))
    assert r.status_code == 403


def test_requires_auth():
    r = client.get(f"/api/platform-archive/patients/{PID}/summary")
    assert r.status_code == 401
