from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# 网关注入身份的请求头（测试里手工模拟）。
# 头只能是 ASCII：scopes 用科室代码；含中文的显示名由网关 URL-encode 下发。
DOCTOR = {
    "X-User-Id": "u1",
    "X-User-Name": "%E6%9D%8E%E5%8C%BB%E7%94%9F",  # URL-encoded 「李医生」
    "X-User-Roles": "doctor",
    "X-User-Scopes": "card",  # 心内科代码
}


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["scenario"] == "001"


def test_followups_requires_auth():
    # 无身份头 → 401（鉴权）
    r = client.get("/api/scenario-001/followups")
    assert r.status_code == 401


def test_followups_scope_filter_and_mask():
    # 心内科医生只看到心内科记录，且姓名脱敏（数据权限 + 脱敏）
    r = client.get("/api/scenario-001/followups", headers=DOCTOR)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["dept"] == "心内科"
    assert body["items"][0]["patient_name"] == "张*"


def test_get_followup_forbidden_cross_dept():
    # 访问非本科室患者记录 → 403（越权）
    r = client.get("/api/scenario-001/followups/f2", headers=DOCTOR)
    assert r.status_code == 403


def test_get_followup_not_found():
    r = client.get("/api/scenario-001/followups/nope", headers=DOCTOR)
    assert r.status_code == 404
