from __future__ import annotations

import patch_workflow_model as pwm


def test_patch_model_updates_llm_nodes() -> None:
    graph = {
        "nodes": [
            {"id": "n1", "data": {"type": "start"}},
            {"id": "n2", "data": {"type": "llm", "model": {"name": "old", "completion_params": {"temperature": 0.9}}}},
            {"id": "n3", "data": {"type": "answer"}},
        ]
    }
    changed = pwm.patch_model(graph, model_name="gpt-5.2-codex", temperature=0.2)
    assert changed == 1
    llm = graph["nodes"][1]["data"]["model"]
    assert llm["name"] == "gpt-5.2-codex"
    assert llm["completion_params"]["temperature"] == 0.2

