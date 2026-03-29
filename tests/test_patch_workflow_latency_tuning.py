from __future__ import annotations

import patch_workflow_latency_tuning as pwlt


def test_patch_latency_updates_retrieval_and_llm() -> None:
    graph = {
        "nodes": [
            {
                "id": "kr1",
                "data": {
                    "type": "knowledge-retrieval",
                    "multiple_retrieval_config": {"top_k": 5, "reranking_enable": True},
                },
            },
            {
                "id": "l1",
                "data": {
                    "type": "llm",
                    "model": {"completion_params": {"temperature": 0.2}},
                },
            },
        ],
        "edges": [],
    }
    retrieval_updated, llm_updated = pwlt.patch_latency(graph, retrieval_top_k=2, llm_max_tokens=700)
    assert retrieval_updated == 1
    assert llm_updated == 1
    kr_cfg = graph["nodes"][0]["data"]["multiple_retrieval_config"]
    assert kr_cfg["top_k"] == 2
    assert kr_cfg["reranking_enable"] is False
    llm_params = graph["nodes"][1]["data"]["model"]["completion_params"]
    assert llm_params["max_tokens"] == 700
    assert llm_params["temperature"] == 0.2
