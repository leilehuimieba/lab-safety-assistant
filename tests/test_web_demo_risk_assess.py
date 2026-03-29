from __future__ import annotations

import importlib.util


FASTAPI_AVAILABLE = importlib.util.find_spec("fastapi") is not None


def test_web_demo_dependency_marker() -> None:
    # CI/本地测试环境不一定安装 web_demo 运行依赖；
    # 该用例保证本测试文件在任意环境都可被收集。
    assert isinstance(FASTAPI_AVAILABLE, bool)


if FASTAPI_AVAILABLE:
    from fastapi.testclient import TestClient
    import app as web_app

    def test_risk_assess_endpoint_returns_structure(monkeypatch) -> None:
        def fake_retrieve(_question: str, top_k: int = 5) -> list[web_app.Citation]:
            return [
                web_app.Citation(
                    kb_id="KB-001",
                    title="酸液飞溅应急处理",
                    source_title="实验室安全手册",
                    source_org="某高校",
                    source_url="https://example.com/rule",
                    risk_level="4",
                    snippet="酸液飞溅应立即冲洗，必须佩戴护目镜和耐化学手套。",
                    score=5.0,
                )
            ][:top_k]

        def fake_match_rule(_question: str) -> dict[str, str]:
            return {"id": "R-001", "severity": "high", "action": "safe_answer", "response": ""}

        monkeypatch.setattr(web_app, "retrieve_citations", fake_retrieve)
        monkeypatch.setattr(web_app, "match_rule", fake_match_rule)
        monkeypatch.setattr(web_app, "append_low_confidence_followup", lambda **_: False)

        client = TestClient(web_app.app)
        resp = client.post("/api/risk_assess", json={"scenario": "使用浓盐酸配液并加热时需要注意什么"})
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["risk_score"] >= 4
        assert payload["risk_level"] in {"高", "极高"}
        assert "化学" in payload["key_hazards"]
        assert "护目镜" in payload["ppe"]
        assert len(payload["recommended_steps"]) > 0
        assert len(payload["forbidden"]) > 0
        assert len(payload["emergency_actions"]) > 0

    def test_chat_terminal_rule_short_circuit(monkeypatch) -> None:
        monkeypatch.setattr(
            web_app,
            "match_rule",
            lambda _question: {
                "id": "R-T",
                "severity": "critical",
                "action": "refuse",
                "response": "该行为属于高风险违规操作。",
            },
        )
        monkeypatch.setattr(web_app, "retrieve_citations", lambda _question, top_k=4: [])

        client = TestClient(web_app.app)
        resp = client.post("/api/chat", json={"mode": "lab", "question": "如何绕过实验室安全制度配制高危试剂"})
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["model"] == "rule-engine"
        assert payload["decision"] == "rule_blocked"
        assert isinstance(payload["answer"], str) and payload["answer"].strip()
