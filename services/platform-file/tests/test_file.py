"""文件元数据 集成测试（连真实 PostgreSQL；依赖 seed_external.py 灌入 P-1001 文件）。"""

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
    db.execute(text("DELETE FROM platform_file.file_object WHERE patient_id='P-TF'"))
    db.commit()
    db.close()


def test_register_and_get():
    r = client.post("/api/platform-file/files", headers=_staff(), json={"filename": "test.pdf", "mime": "application/pdf", "patient_id": "P-TF", "scenario": "test"})
    assert r.status_code == 201
    fid = r.json()["file_id"]
    assert r.json()["storage_uri"].startswith("minio://")
    g = client.get(f"/api/platform-file/files/{fid}", headers=_staff())
    assert g.status_code == 200 and g.json()["filename"] == "test.pdf"


def test_seeded_patient_files():
    r = client.get("/api/platform-file/patients/P-1001/files", headers=_staff())
    assert r.status_code == 200 and len(r.json()) >= 2


def test_patient_self_vs_other():
    assert client.get("/api/platform-file/patients/P-1001/files", headers=_patient("P-1001")).status_code == 200
    assert client.get("/api/platform-file/patients/P-1001/files", headers=_patient("P-9999")).status_code == 403


def test_register_requires_clinical():
    r = client.post("/api/platform-file/files", headers=_patient("P-TF"), json={"filename": "x.pdf"})
    assert r.status_code == 403


def test_requires_auth():
    assert client.get("/api/platform-file/patients/P-1001/files").status_code == 401
