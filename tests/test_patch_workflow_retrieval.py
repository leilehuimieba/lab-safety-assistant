from __future__ import annotations

import patch_workflow_retrieval as pwr


def test_patch_disable_retrieval_removes_node_and_relinks_start_to_llm() -> None:
    graph = {
        "nodes": [
            {"id": "start1", "data": {"type": "start"}},
            {"id": "kr1", "data": {"type": "knowledge-retrieval"}},
            {"id": "llm1", "data": {"type": "llm", "context": {"enabled": True, "variable_selector": ["kr1", "result"]}}},
            {"id": "ans1", "data": {"type": "answer"}},
        ],
        "edges": [
            {"id": "e1", "source": "start1", "target": "kr1"},
            {"id": "e2", "source": "kr1", "target": "llm1"},
            {"id": "e3", "source": "llm1", "target": "ans1"},
        ],
    }

    patched, removed_ids, added_edges = pwr.patch_disable_retrieval(graph)
    node_ids = {str(node.get("id")) for node in patched["nodes"]}
    edge_pairs = {(str(edge.get("source")), str(edge.get("target"))) for edge in patched["edges"]}

    assert removed_ids == ["kr1"]
    assert "kr1" not in node_ids
    assert ("start1", "llm1") in edge_pairs
    assert added_edges == 1

    llm = next(node for node in patched["nodes"] if node.get("id") == "llm1")
    assert llm["data"]["context"]["enabled"] is False
    assert llm["data"]["context"]["variable_selector"] == []

