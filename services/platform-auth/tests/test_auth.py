"""登录鉴权 集成测试（DB 认证，连真实 PostgreSQL；依赖 seed_external.py 灌入身份）。"""

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from py_common import decode_token

client = TestClient(app)


def test_login_success_from_db():
    r = client.post("/api/platform-auth/login", json={"username": "doctor_card", "password": "123456"})
    assert r.status_code == 200
    body = r.json()
    assert body["user_id"] == "u1"
    assert "doctor" in body["roles"]
    assert body["scopes"] == ["card"]  # user_data_scope custom/card
    # caps 来自 staff_scenario_enrollment + enrollment_capability
    assert "referral:receive" in body["caps"] and "homebed:manage" in body["caps"]
    payload = decode_token(body["token"], settings.jwt_secret)
    assert payload["sub"] == "u1"


def test_patient_login_resolves_patient_id():
    r = client.post("/api/platform-auth/login", json={"username": "patient_zjg", "password": "123456"})
    assert r.status_code == 200
    body = r.json()
    assert "resident" in body["roles"]
    assert body["patient_id"] == "P-1001"  # patient_guardian relation=本人


def test_login_wrong_password():
    r = client.post("/api/platform-auth/login", json={"username": "doctor_card", "password": "bad"})
    assert r.status_code == 401


def test_login_unknown_user():
    r = client.post("/api/platform-auth/login", json={"username": "ghost", "password": "x"})
    assert r.status_code == 401


def test_refresh_and_logout():
    login = client.post("/api/platform-auth/login", json={"username": "doctor_card", "password": "123456"}).json()
    rt = login["refresh_token"]
    # 刷新换新访问令牌
    r = client.post("/api/platform-auth/refresh", json={"refresh_token": rt})
    assert r.status_code == 200 and r.json()["token"]
    # 登出后该刷新令牌不可再用
    assert client.post("/api/platform-auth/logout", json={"refresh_token": rt}).status_code == 200
    assert client.post("/api/platform-auth/refresh", json={"refresh_token": rt}).status_code == 401
