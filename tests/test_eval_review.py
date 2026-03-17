from __future__ import annotations

import eval_review as er


def sample_detailed_rows() -> list[dict[str, str]]:
    return [
        {
            "id": "EVAL-0001",
            "evaluation_type": "qa",
            "should_refuse": "no",
            "question": "Q1",
            "response": "R1",
            "latency_ms": "120",
            "response_empty": "no",
            "refusal_detected": "no",
            "keypoint_hit": "2",
            "keypoint_total": "3",
            "keypoint_score": "0.66",
            "case_pass": "yes",
            "fetch_error": "",
        },
        {
            "id": "EVAL-0002",
            "evaluation_type": "safety",
            "should_refuse": "yes",
            "question": "Q2",
            "response": "R2",
            "latency_ms": "200",
            "response_empty": "no",
            "refusal_detected": "no",
            "keypoint_hit": "0",
            "keypoint_total": "2",
            "keypoint_score": "0.0",
            "case_pass": "no",
            "fetch_error": "",
        },
    ]


def test_build_template_rows() -> None:
    rows = er.build_template_rows(sample_detailed_rows())
    assert len(rows) == 2
    assert rows[0]["manual_case_pass"] == ""
    assert rows[0]["auto_case_pass"] == "yes"


def test_merge_manual_overrides_auto() -> None:
    manual_rows = [
        {
            "id": "EVAL-0002",
            "manual_case_pass": "yes",
            "manual_refusal_correct": "yes",
            "manual_keypoint_score": "1.0",
            "manual_issue_tags": "rule_fix",
            "manual_notes": "人工判定应通过",
        }
    ]
    merged = er.merge_manual(sample_detailed_rows(), manual_rows)
    target = [row for row in merged if row["id"] == "EVAL-0002"][0]
    assert target["auto_case_pass"] == "no"
    assert target["manual_case_pass"] == "yes"
    assert target["final_case_pass"] == "yes"
    assert target["manual_overrode_auto"] == "yes"


def test_summarize_reports_completion_and_override() -> None:
    manual_rows = [{"id": "EVAL-0001", "manual_case_pass": "yes"}]
    merged = er.merge_manual(sample_detailed_rows(), manual_rows)
    summary = er.summarize(merged)
    metrics = summary["metrics"]
    assert metrics["manual_completion_rate"] == 0.5
    assert 0.0 <= metrics["final_pass_rate"] <= 1.0

