"""platform-ai 规则引擎单元测试（无需 Anthropic API Key）。

测试覆盖：
- 处方审方：passed / warn / rejected 三条路径
- AI 分诊：P1 / P2 / P3 三级
- HTTP 接口：鉴权缺失 401
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.routes import _rule_rx_review, _rule_triage

client = TestClient(app, raise_server_exceptions=True)

_AUTH = {
    "X-User-Id": "u_test",
    "X-User-Name": "测试医生",
    "X-User-Roles": "doctor",
    "X-User-Scopes": "card",
    "X-User-Caps": "teleconsult:treat",
}


# ---- 规则引擎单元测试 -------------------------------------------------------

class TestRxReviewRules:
    def test_safe_drug_passes(self):
        result = _rule_rx_review("阿莫地平片", "一日1次，每次5mg", None)
        assert result["result"] == "passed"

    def test_nsaid_with_anticoagulant_warns(self):
        result = _rule_rx_review("布洛芬缓释胶囊", "一日3次", "华法林抗凝治疗中")
        assert result["result"] == "warn"
        assert result["note"]

    def test_nsaid_alone_passes(self):
        result = _rule_rx_review("双氯芬酸钠", "一日2次", None)
        assert result["result"] == "passed"

    def test_penicillin_allergy_rejected(self):
        result = _rule_rx_review("阿莫西林胶囊", "一日3次", "患者有青霉素过敏史")
        assert result["result"] == "rejected"
        assert "过敏" in (result["note"] or "")

    def test_antibiotic_no_allergy_passes(self):
        result = _rule_rx_review("左氧氟沙星片", "一日2次", "无过敏史")
        assert result["result"] == "passed"

    def test_unknown_drug_passes(self):
        result = _rule_rx_review("某种新药XYZ", None, None)
        assert result["result"] == "passed"


class TestTriageRules:
    def test_chest_pain_is_p1(self):
        result = _rule_triage("胸痛30分钟，伴出汗", None)
        assert result["priority"] == "P1"

    def test_fever_is_p2(self):
        result = _rule_triage("发热3天，体温38.5℃，咳嗽", "resp")
        assert result["priority"] == "P2"

    def test_chronic_followup_is_p3(self):
        result = _rule_triage("慢病随访，调整用药", None)
        assert result["priority"] == "P3"

    def test_vomiting_is_p2(self):
        result = _rule_triage("恶心呕吐2天，进食困难", None)
        assert result["priority"] == "P2"


# ---- HTTP 接口测试 ----------------------------------------------------------

class TestRxReviewEndpoint:
    def test_unauthenticated_returns_401(self):
        resp = client.post("/api/platform-ai/rx-review", json={"drug_name": "布洛芬"})
        assert resp.status_code == 401

    def test_authenticated_safe_drug(self):
        resp = client.post(
            "/api/platform-ai/rx-review",
            json={"drug_name": "阿莫地平片", "usage": "每日1片"},
            headers=_AUTH,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["result"] == "passed"
        assert data["engine"] == "rule"

    def test_authenticated_nsaid_anticoagulant_warn(self):
        resp = client.post(
            "/api/platform-ai/rx-review",
            json={"drug_name": "布洛芬片", "usage": "一日3次", "patient_context": "正在服用华法林"},
            headers=_AUTH,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["result"] == "warn"
        assert data["note"]

    def test_rejected_returns_correct_result(self):
        resp = client.post(
            "/api/platform-ai/rx-review",
            json={"drug_name": "青霉素注射液", "patient_context": "有β-内酰胺过敏史"},
            headers=_AUTH,
        )
        assert resp.status_code == 200
        assert resp.json()["result"] == "rejected"


class TestTriageEndpoint:
    def test_unauthenticated_returns_401(self):
        resp = client.post("/api/platform-ai/triage", json={"chief_complaint": "头痛"})
        assert resp.status_code == 401

    def test_p1_triage(self):
        resp = client.post(
            "/api/platform-ai/triage",
            json={"chief_complaint": "突发意识不清，呼之不应"},
            headers=_AUTH,
        )
        assert resp.status_code == 200
        assert resp.json()["priority"] == "P1"

    def test_p3_triage(self):
        resp = client.post(
            "/api/platform-ai/triage",
            json={"chief_complaint": "复诊调药，血压控制良好"},
            headers=_AUTH,
        )
        assert resp.status_code == 200
        assert resp.json()["priority"] == "P3"


class TestHealthEndpoint:
    def test_health_ok(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
