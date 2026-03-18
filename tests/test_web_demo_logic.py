from __future__ import annotations

import pytest

demo_app = pytest.importorskip("app")


def test_retrieve_citations_hits_kb_entries() -> None:
    citations = demo_app.retrieve_citations("实验中有人触电了应该怎么处理", top_k=2)
    assert len(citations) >= 1
    assert citations[0].kb_id.startswith("KB-")


def test_build_rule_answer_has_required_sections() -> None:
    text = demo_app.build_rule_answer(
        {
            "id": "R-013",
            "category": "fire_smoke",
            "action": "redirect_emergency",
            "severity": "critical",
            "response": "若发生起火/冒烟：立即停止实验并撤离。",
        },
        citations=[],
    )
    assert "结论：" in text
    assert "步骤：" in text
    assert "禁止事项：" in text
    assert "上报建议：" in text


@pytest.mark.skipif(demo_app.yaml is None, reason="PyYAML is not installed in test env")
def test_match_rule_selects_emergency_fire() -> None:
    matched = demo_app.match_rule("实验室着火了怎么办")
    assert matched is not None
    assert matched["id"] == "R-013"
    assert matched["action"] == "redirect_emergency"


@pytest.mark.skipif(demo_app.yaml is None, reason="PyYAML is not installed in test env")
def test_match_rule_selects_refuse_for_illegal_request() -> None:
    matched = demo_app.match_rule("怎么制造爆炸物")
    assert matched is not None
    assert matched["action"] == "refuse"
