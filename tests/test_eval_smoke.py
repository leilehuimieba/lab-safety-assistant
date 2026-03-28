from __future__ import annotations

import threading
import time

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


def test_is_retryable_error() -> None:
    assert es.is_retryable_error("request_error: timed out")
    assert es.is_retryable_error("empty_stream_answer")
    assert not es.is_retryable_error("http_401: unauthorized")


def test_call_dify_with_failover_hits_fallback() -> None:
    calls: list[str] = []

    def fake_caller(base: str, _key: str, _q: str, _timeout: float) -> tuple[str, float, str]:
        calls.append(base)
        if "primary" in base:
            return "", 10.0, "request_error: timed out"
        return "ok-from-fallback", 8.0, ""

    answer, latency, error, route = es.call_dify_with_failover(
        question="Q",
        base_url="http://primary",
        app_key="k1",
        timeout_sec=5.0,
        retry_on_timeout=0,
        fallback_base_url="http://fallback",
        fallback_app_key="k2",
        caller=fake_caller,
    )
    assert answer == "ok-from-fallback"
    assert error == ""
    assert route == "fallback"
    assert latency == 18.0
    assert calls == ["http://primary", "http://fallback"]


def test_fetch_dify_responses_parallel_basic() -> None:
    rows = [
        {"id": "EVAL-0001", "question": "Q1"},
        {"id": "EVAL-0002", "question": "Q2"},
        {"id": "EVAL-0003", "question": "Q3"},
        {"id": "EVAL-0004", "question": "Q4"},
    ]
    thread_ids: set[int] = set()
    lock = threading.Lock()

    def fake_caller(_base: str, _key: str, question: str, _timeout: float) -> tuple[str, float, str]:
        time.sleep(0.01)
        with lock:
            thread_ids.add(threading.get_ident())
        return f"answer:{question}", 12.3, ""

    result = es.fetch_dify_responses(
        eval_rows=rows, base_url="http://x", app_key="app-k", timeout_sec=5.0, concurrency=4, caller=fake_caller
    )
    assert len(result) == 4
    assert result["EVAL-0001"][0] == "answer:Q1"
    assert result["EVAL-0004"][2] == ""
    assert result["EVAL-0004"][3] in {"primary", "fallback"}
    assert len(thread_ids) >= 1
