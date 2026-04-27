from __future__ import annotations

import ai_review_kb as ark


def test_extract_first_json_object_from_wrapped_text() -> None:
    text = "prefix text\n{\"decision\":\"pass\",\"score\":88}\npostfix"
    extracted = ark.extract_first_json_object(text)
    assert extracted.startswith("{")
    assert '"decision":"pass"' in extracted


def test_parse_review_json_ok() -> None:
    raw = "{\"decision\":\"needs_fix\",\"score\":55,\"safety_ok\":false}"
    parsed, err = ark.parse_review_json(raw)
    assert not err
    assert parsed["decision"] == "needs_fix"
    assert parsed["score"] == 55


def test_post_rule_check_for_high_risk_missing_fields() -> None:
    row = {
        "risk_level": "4",
        "answer": "这是一个高风险场景的简短回答，但缺少关键约束信息。",
        "forbidden": "",
        "emergency": "",
    }
    issue = ark.post_rule_check(row, strict_high_risk=True)
    assert "high_risk_missing_forbidden" in issue
    assert "high_risk_missing_emergency" in issue

