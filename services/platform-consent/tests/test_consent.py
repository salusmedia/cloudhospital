"""数据授权 集成测试（连真实 PostgreSQL；依赖 seed_external.py 灌入 P-1001 授权）。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import SessionFactory
from app.main import app

client = TestClient(app)


def _staff() -> dict[str, str]:
    return {"X-User-Id": "u1", "X-User-Roles": "doctor", "X-User-Scopes": "card"}


def _patient(pid: str) -> dict[str, str]:
    return {"X-User-Id": "pt", "X-User-Roles": "resident", "X-User-Patient-Id": pid}


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    db = SessionFactory()
    db.execute(text("DELETE FROM platform_consent.consent_record WHERE patient_id='P-TC'"))
    db.commit()
    db.close()


def test_seeded_list():
    r = client.get("/api/platform-consent/patients/P-1001/consents", headers=_staff())
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) >= 3
    assert {x["status"] for x in rows} >= {"granted", "revoked"}


def test_patient_grant_then_revoke():
    g = client.post("/api/platform-consent/consents", headers=_patient("P-TC"), json={"patient_id": "P-TC", "grantee": "ai_assistant", "purpose": "测试授权"})
    assert g.status_code == 201 and g.json()["status"] == "granted"
    cid = g.json()["id"]
    rv = client.post(f"/api/platform-consent/consents/{cid}/revoke", headers=_patient("P-TC"))
    assert rv.status_code == 200 and rv.json()["status"] == "revoked"


def test_cannot_manage_others_consent():
    r = client.post("/api/platform-consent/consents", headers=_patient("P-9999"), json={"patient_id": "P-1001", "grantee": "x", "purpose": "y"})
    assert r.status_code == 403


def test_requires_auth():
    assert client.get("/api/platform-consent/patients/P-1001/consents").status_code == 401
