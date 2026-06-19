"""端到端鉴权链路测试：用 monkeypatch 拦截转发，验证网关在转发前的鉴权与身份注入。"""

import pytest
from fastapi.testclient import TestClient

from app import main, proxy
from app.config import settings
from py_common import create_token

client = TestClient(main.app)


@pytest.fixture
def captured(monkeypatch):
    """拦截 proxy.forward，记录转发参数，返回固定上游响应。"""
    calls: list[dict] = []

    async def fake_forward(method, url, headers, body, *, timeout=30.0):
        calls.append({"method": method, "url": url, "headers": headers, "body": body})
        return proxy.UpstreamResponse(200, b'{"data":"ok"}', {"content-type": "application/json"})

    monkeypatch.setattr(proxy, "forward", fake_forward)
    return calls


def _token():
    return create_token(
        {
            "sub": "u1",
            "name": "李医生",
            "roles": ["doctor"],
            "scopes": ["card"],
            "caps": ["referral:receive"],
        },
        secret=settings.jwt_secret,
    )


def test_protected_route_without_token_is_401(captured):
    r = client.get("/api/scenario-001/followups")
    assert r.status_code == 401
    assert r.json()["code"] == "NO_TOKEN"
    assert captured == []  # 未转发


def test_protected_route_with_bad_token_is_401(captured):
    r = client.get(
        "/api/scenario-001/followups", headers={"Authorization": "Bearer garbage"}
    )
    assert r.status_code == 401
    assert r.json()["code"] == "BAD_TOKEN"
    assert captured == []


def test_valid_token_injects_identity_and_forwards(captured):
    r = client.get(
        "/api/scenario-001/followups",
        headers={"Authorization": f"Bearer {_token()}", "X-User-Id": "spoofed"},
    )
    assert r.status_code == 200
    assert len(captured) == 1
    fwd = captured[0]
    # 转发到正确上游
    assert fwd["url"].endswith("/api/scenario-001/followups")
    assert "scenario-001-backend:8001" in fwd["url"]
    # 注入可信身份，且伪造的 X-User-Id 被覆盖/剥离
    assert fwd["headers"]["X-User-Id"] == "u1"
    assert fwd["headers"]["X-User-Scopes"] == "card"
    assert fwd["headers"]["X-User-Caps"] == "referral:receive"
    assert fwd["headers"]["X-User-Name"] == "%E6%9D%8E%E5%8C%BB%E7%94%9F"
    # 原始 Authorization 不下传
    assert "Authorization" not in fwd["headers"]
    assert "authorization" not in {k.lower() for k in fwd["headers"]}


def test_public_login_route_forwards_without_token(captured):
    r = client.post("/api/platform-auth/login", json={"username": "x", "password": "y"})
    assert r.status_code == 200
    assert len(captured) == 1
    fwd = captured[0]
    assert "platform-auth:8101" in fwd["url"]
    assert "X-User-Id" not in fwd["headers"]  # public 不注入身份


def test_unknown_route_is_404(captured):
    r = client.get("/api/does-not-exist")
    assert r.status_code == 404
    assert captured == []
