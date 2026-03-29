from __future__ import annotations

import patch_workflow_retrieval_keyword_only as pwrko


def test_patch_keyword_only_updates_weights() -> None:
    graph = {
        "nodes": [
            {
                "id": "kr1",
                "data": {
                    "type": "knowledge-retrieval",
                    "retrieval_mode": "multiple",
                    "multiple_retrieval_config": {
                        "weights": {
                            "weight_type": "customized",
                            "vector_setting": {"vector_weight": 0.7, "embedding_provider_name": "x"},
                            "keyword_setting": {"keyword_weight": 0.3},
                        }
                    },
                },
            }
        ],
        "edges": [],
    }
    updated, node_ids = pwrko.patch_keyword_only(graph)
    assert updated == 1
    assert node_ids == ["kr1"]
    data = graph["nodes"][0]["data"]
    cfg = data["multiple_retrieval_config"]
    assert cfg["weights"]["vector_setting"]["vector_weight"] == 0.0
    assert cfg["weights"]["keyword_setting"]["keyword_weight"] == 1.0
