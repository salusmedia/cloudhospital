"""患者主数据 集成测试（连真实 PostgreSQL）。

证明：
- 敏感字段加密落盘（库里存的不是明文）。
- 读取统一脱敏（姓名/身份证/手机号都被掩码）。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import SessionFactory
from app.main import app

client = TestClient(app)

PID = "TST-PT-001"


def _hdr() -> dict[str, str]:
    return {
        "X-User-Id": "test_doc",
        "X-User-Name": "%E7%8E%8B%E5%8C%BB%E7%94%9F",
        "X-User-Roles": "doctor",
        "X-User-Scopes": "card",
    }


def _cleanup(db) -> None:
    db.execute(text("DELETE FROM platform_patient.patient WHERE patient_id=:p"), {"p": PID})
    db.commit()


@pytest.fixture(scope="module", autouse=True)
def around():
    db = SessionFactory()
    _cleanup(db)
    db.close()
    yield
    db = SessionFactory()
    _cleanup(db)
    db.close()


def test_create_and_read_desensitized():
    r = client.post(
        "/api/platform-patient/patients",
        headers=_hdr(),
        json={
            "patient_id": PID, "name": "张三丰",
            "id_card": "330302199001011234", "phone": "13800138000",
            "gender": "M", "org_id": "wzcvh",
        },
    )
    assert r.status_code == 201

    r = client.get(f"/api/platform-patient/patients/{PID}", headers=_hdr())
    assert r.status_code == 200
    body = r.json()
    # 读出来是脱敏的
    assert body["name"] == "张*丰"
    assert body["id_card"] == "330302********1234"
    assert body["phone"] == "138****8000"


def test_stored_value_is_encrypted_not_plaintext():
    db = SessionFactory()
    raw = db.execute(
        text("SELECT name_enc FROM platform_patient.patient WHERE patient_id=:p"),
        {"p": PID},
    ).scalar()
    db.close()
    assert raw is not None
    # 密文里不应出现“张”(UTF-8: e5 bc a0) —— 证明落盘是加密的
    assert "张".encode("utf-8") not in bytes(raw)


def test_missing_patient_404():
    r = client.get("/api/platform-patient/patients/NOPE", headers=_hdr())
    assert r.status_code == 404


def test_requires_auth():
    r = client.get(f"/api/platform-patient/patients/{PID}")
    assert r.status_code == 401
