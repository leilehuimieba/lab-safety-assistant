from __future__ import annotations

import eval_smoke as es


def test_split_segments_handles_cn_and_semicolon() -> None:
    assert es.split_segments("A;B； C ") == ["A", "B", "C"]


def test_keypoint_hit_score_supports_option_tokens() -> None:
    answer = "处理流程包括撤离现场，并立即报警。"
    score, hit, total = es.keypoint_hit_score(answer, "撤离/疏散;报警/报告;冲洗")
    assert total == 3
    assert hit == 2
    assert round(score, 4) == round(2 / 3, 4)


def test_detect_refusal_and_non_refusal() -> None:
    assert es.detect_refusal("这是高风险操作，我不能提供具体步骤。")
    assert not es.detect_refusal("请佩戴护目镜并按SOP操作。")


def test_percentile_interpolates() -> None:
    values = [100.0, 200.0, 400.0, 1000.0]
    p95 = es.percentile(values, 0.95)
    assert 900.0 <= p95 <= 1000.0


def test_resolve_chat_endpoint_variants() -> None:
    assert es.resolve_chat_endpoint("http://localhost") == "http://localhost/v1/chat-messages"
    assert es.resolve_chat_endpoint("http://localhost/v1") == "http://localhost/v1/chat-messages"

