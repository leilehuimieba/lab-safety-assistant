from __future__ import annotations

import patch_workflow_minimal as pwm


def test_build_minimal_graph_keeps_three_core_nodes() -> None:
    source = {
        "nodes": [
            {"id": "s1", "data": {"type": "start"}},
            {
                "id": "l1",
                "data": {"type": "llm", "model": {"provider": "x", "name": "m", "mode": "chat"}},
            },
            {"id": "a1", "data": {"type": "answer"}},
            {"id": "kr1", "data": {"type": "knowledge-retrieval"}},
        ],
        "edges": [],
    }
    result = pwm.build_minimal_graph(source)
    assert len(result["nodes"]) == 3
    assert len(result["edges"]) == 2
    types = [node["data"]["type"] for node in result["nodes"]]
    assert types == ["start", "llm", "answer"]
    answer = result["nodes"][2]["data"]["answer"]
    assert answer == "{{#l1.text#}}"

