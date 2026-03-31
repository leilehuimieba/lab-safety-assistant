from __future__ import annotations

import importlib.util


FASTAPI_AVAILABLE = importlib.util.find_spec("fastapi") is not None


def test_web_demo_dependency_marker() -> None:
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
                    snippet="酸液飞溅应立即冲洗，并佩戴护目镜和耐化学手套。",
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
        assert payload["risk_level"] in {"高", "极高", "High", "Critical"}
        assert any(item in payload["key_hazards"] for item in {"化学", "Chemical"})
        assert any(item in payload["ppe"] for item in {"护目镜", "Splash goggles"})
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

    def test_chat_low_confidence_fallback_and_followup(monkeypatch) -> None:
        citations = [
            web_app.Citation(
                kb_id="KB-X",
                title="Low match item",
                source_title="Low confidence source",
                score=0.4,
            )
        ]
        monkeypatch.setattr(web_app, "retrieve_citations", lambda _q, top_k=4: citations[:top_k])
        monkeypatch.setattr(web_app, "match_rule", lambda _q: None)
        monkeypatch.setattr(
            web_app,
            "call_upstream",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(web_app.HTTPException(status_code=502, detail="x")),
        )
        monkeypatch.setattr(web_app, "append_low_confidence_followup", lambda **_: True)

        client = TestClient(web_app.app)
        resp = client.post("/api/chat", json={"mode": "lab", "question": "未知新试剂泄漏怎么处理"})
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["decision"] == "llm_fallback_structured"
        assert payload["model"] == "fallback-rule-engine"
        assert payload["low_confidence"] is True
        assert payload["followup_logged"] is True
        assert "附注：" in payload["answer"]
