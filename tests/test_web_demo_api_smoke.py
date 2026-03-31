from __future__ import annotations

import importlib.util


FASTAPI_AVAILABLE = importlib.util.find_spec("fastapi") is not None


def test_web_demo_smoke_dependency_marker() -> None:
    assert isinstance(FASTAPI_AVAILABLE, bool)


if FASTAPI_AVAILABLE:
    from fastapi.testclient import TestClient
    import app as web_app

    def test_sanitize_llm_output_removes_think_block() -> None:
        raw = "<think>internal reasoning</think>\nConclusion:\nUse the approved SOP."
        assert web_app.sanitize_llm_output(raw) == "Conclusion:\nUse the approved SOP."

    def test_chat_llm_guarded_path(monkeypatch) -> None:
        citations = [
            web_app.Citation(
                kb_id="KB-SMOKE-1",
                title="Chemical Lab PPE Rule",
                source_title="Lab Safety Manual",
                source_org="Test University",
                source_url="https://example.com/lab-rule",
                risk_level="4",
                snippet="Use goggles and chemical-resistant gloves for corrosive handling.",
                score=5.2,
            )
        ]

        monkeypatch.setattr(web_app, "retrieve_citations", lambda _q, top_k=4: citations[:top_k])
        monkeypatch.setattr(
            web_app,
            "match_rule",
            lambda _q: {"id": "R-LAB-1", "action": "safe_answer", "severity": "high", "response": "Follow strict PPE controls."},
        )
        monkeypatch.setattr(web_app, "call_upstream", lambda *_args, **_kwargs: ("Structured safe answer.", "gpt-5.2-codex"))

        client = TestClient(web_app.app)
        resp = client.post("/api/chat", json={"mode": "lab", "question": "How to handle concentrated acid safely?"})
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["decision"] == "llm_answer_guarded"
        assert payload["model"] == "gpt-5.2-codex"
        assert payload["matched_rule_id"] == "R-LAB-1"
        assert len(payload["citations"]) >= 1

    def test_search_endpoint_returns_citations(monkeypatch) -> None:
        monkeypatch.setattr(
            web_app,
            "retrieve_citations",
            lambda _q, top_k=5: [
                web_app.Citation(
                    kb_id="KB-S-1",
                    title="Emergency Shower Rule",
                    source_title="EHS SOP",
                    source_org="Test University",
                    source_url="https://example.com/ehs",
                    risk_level="3",
                    snippet="Flush exposed area for at least 15 minutes.",
                    score=4.6,
                )
            ][:top_k],
        )

        client = TestClient(web_app.app)
        resp = client.get("/api/search", params={"q": "acid splash", "top_k": 3})
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["query"] == "acid splash"
        assert payload["count"] == 1
        assert payload["citations"][0]["kb_id"] == "KB-S-1"
