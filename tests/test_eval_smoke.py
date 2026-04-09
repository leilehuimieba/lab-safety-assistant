from __future__ import annotations

import threading
import time
from unittest.mock import patch

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
    assert es.detect_refusal("\u4e0d\u80fd\u63d0\u4f9b\u5177\u4f53\u64cd\u4f5c\u6b65\u9aa4\u3002")
    assert es.detect_refusal("answer: \u4e0d\u53ef\u4ee5\u8fdb\u884c\u8fd9\u7c7b\u64cd\u4f5c\u3002")
    assert not es.detect_refusal("\u8bf7\u4f69\u6234\u62a4\u76ee\u955c\u5e76\u6309SOP\u64cd\u4f5c\u3002")


def test_detect_prohibition() -> None:
    assert es.detect_prohibition("\u8fc7\u671f\u8bd5\u5242\u4e0d\u80fd\u76f4\u63a5\u5012\u6389\u3002")
    assert es.detect_prohibition("\u7981\u6b62\u6df7\u5408\u76d0\u9178\u4e0e\u6f02\u767d\u6c34\u3002")
    assert not es.detect_prohibition("\u8bf7\u4f7f\u7528\u901a\u98ce\u67dc\u64cd\u4f5c\u3002")


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
    assert es.is_retryable_error(
        "workflow_error: [models] Server Unavailable Error, ('Connection aborted.', ConnectionResetError(104, 'Connection reset by peer'))"
    )
    assert es.is_retryable_error("request_error: ('Connection aborted.', RemoteDisconnected('Remote end closed connection'))")
    assert not es.is_retryable_error("http_401: unauthorized")


def test_call_dify_with_failover_retries_connection_reset_on_primary() -> None:
    calls: list[str] = []

    def fake_caller(
        base: str, _key: str, _q: str, _timeout: float, _response_mode: str = "streaming"
    ) -> tuple[str, float, str]:
        calls.append(base)
        if len(calls) == 1:
            return "", 7.0, "workflow_error: [models] Server Unavailable Error, ('Connection aborted.', ConnectionResetError(104, 'Connection reset by peer'))"
        return "ok-after-retry", 6.0, ""

    answer, latency, error, route = es.call_dify_with_failover(
        question="Q",
        base_url="http://primary",
        app_key="k1",
        timeout_sec=5.0,
        retry_on_timeout=1,
        fallback_base_url="http://fallback",
        fallback_app_key="k2",
        caller=fake_caller,
    )
    assert answer == "ok-after-retry"
    assert error == ""
    assert route == "primary"
    assert latency == 13.0
    assert calls == ["http://primary", "http://primary"]


def test_call_dify_with_failover_hits_fallback() -> None:
    calls: list[str] = []

    def fake_caller(
        base: str, _key: str, _q: str, _timeout: float, _response_mode: str = "streaming"
    ) -> tuple[str, float, str]:
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


def test_extract_workflow_output_text_prefers_non_empty_string() -> None:
    outputs = {"foo": "", "result": "final text", "text": ""}
    assert es.extract_workflow_output_text(outputs) == "final text"


def test_call_dify_accepts_workflow_finished_output_after_message_end() -> None:
    class FakeResponse:
        status_code = 200
        headers = {"Content-Type": "text/event-stream; charset=utf-8"}
        text = ""

        def iter_lines(self, decode_unicode: bool = True):
            yield 'data: {"event":"message_end"}'
            yield 'data: {"event":"workflow_finished","data":{"outputs":{"result":"最终答案"},"error":null}}'

    with patch("eval_smoke.requests.post", return_value=FakeResponse()):
        answer, latency_ms, error = es.call_dify(
            base_url="http://localhost:8080",
            app_key="app-test",
            question="Q",
            timeout_sec=5.0,
            response_mode="streaming",
        )

    assert answer == "最终答案"
    assert error == ""
    assert latency_ms >= 0.0


def test_fetch_dify_responses_parallel_basic() -> None:
    rows = [
        {"id": "EVAL-0001", "question": "Q1"},
        {"id": "EVAL-0002", "question": "Q2"},
        {"id": "EVAL-0003", "question": "Q3"},
        {"id": "EVAL-0004", "question": "Q4"},
    ]
    thread_ids: set[int] = set()
    lock = threading.Lock()

    def fake_caller(
        _base: str, _key: str, question: str, _timeout: float, _response_mode: str = "streaming"
    ) -> tuple[str, float, str]:
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
