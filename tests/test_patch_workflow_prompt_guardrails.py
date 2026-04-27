from __future__ import annotations

import patch_workflow_prompt_guardrails as ppg


def test_build_guardrail_prompt_template_has_required_sections() -> None:
    prompt = ppg.build_guardrail_prompt_template()
    assert len(prompt) == 2
    assert prompt[0]["role"] == "system"
    assert prompt[1]["role"] == "user"
    system_text = prompt[0]["text"]
    for marker in ["answer:", "steps:", "ppe:", "forbidden:", "emergency:"]:
        assert marker in system_text
    assert "至少4条" in system_text
    assert "关键点召回强化" in system_text
    assert "有机废液桶" in system_text
    assert "关键短语命中优先" in system_text
    assert "先断电、绝缘隔离、急救、报警" in system_text
    assert "必须以“不能。”或“禁止。”开头" in system_text


def test_patch_graph_updates_llm_prompt_and_answer_binding() -> None:
    graph = {
        "nodes": [
            {"id": "s1", "data": {"type": "start"}},
            {
                "id": "l1",
                "data": {
                    "type": "llm",
                    "prompt_template": [{"role": "system", "text": "old"}],
                },
            },
            {"id": "a1", "data": {"type": "answer", "answer": "{{#wrong.text#}}"}},
        ],
        "edges": [],
    }
    llm_updated, llm_ids = ppg.patch_llm_prompt_templates(graph)
    assert llm_updated == 1
    assert llm_ids == ["l1"]
    answer_updated = ppg.patch_answer_binding(graph, llm_ids)
    assert answer_updated == 1
    answer_value = graph["nodes"][2]["data"]["answer"]
    assert answer_value == "{{#l1.text#}}"
