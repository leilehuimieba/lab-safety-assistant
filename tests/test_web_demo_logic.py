from __future__ import annotations

from pathlib import Path

import pytest

demo_app = pytest.importorskip("app")


def test_retrieve_citations_hits_kb_entries() -> None:
    citations = demo_app.retrieve_citations("实验中有人触电了应该怎么处理", top_k=2)
    assert len(citations) >= 1
    assert citations[0].kb_id.startswith("KB-")


def test_assess_low_confidence_when_empty() -> None:
    low, reason = demo_app.assess_low_confidence([])
    assert low
    assert "未命中" in reason


def test_assess_low_confidence_for_high_score_with_source() -> None:
    citations = [
        demo_app.Citation(
            kb_id="KB-9999",
            title="测试条目",
            source_title="测试来源",
            source_org="测试机构",
            score=8.2,
        )
    ]
    low, reason = demo_app.assess_low_confidence(citations)
    assert not low
    assert reason == ""


def test_append_low_confidence_followup_deduplicates(tmp_path: Path) -> None:
    queue_file = tmp_path / "queue.csv"
    citations: list[demo_app.Citation] = []
    first = demo_app.append_low_confidence_followup(
        question="这个新仪器怎么处理异常报警？",
        mode="lab",
        decision="llm_low_confidence",
        risk_level="medium",
        matched_rule_id="",
        matched_rule_action="",
        low_confidence_reason="未命中知识库条目",
        citations=citations,
        queue_file=queue_file,
    )
    second = demo_app.append_low_confidence_followup(
        question="这个新仪器怎么处理异常报警？",
        mode="lab",
        decision="llm_low_confidence",
        risk_level="medium",
        matched_rule_id="",
        matched_rule_action="",
        low_confidence_reason="未命中知识库条目",
        citations=citations,
        queue_file=queue_file,
    )
    assert first is True
    assert second is False


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
