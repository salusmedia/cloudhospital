from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["scenario"] == "019"


def test_ping():
    r = client.get("/api/scenario-019/ping")
    assert r.status_code == 200
    assert r.json()["message"] == "pong"
