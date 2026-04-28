from __future__ import annotations

"""应用元信息服务

- get_demo_meta: 返回应用版本、知识库规模、运行时模型等元数据
"""

import os

from ..models import DemoMetaResponse
from ..repositories import (
    APP_VERSION,
    FORMAL_EVAL_SCORE,
    STABILITY_EVIDENCE,
    KB_IMPORT_SUCCESS_COUNT,
    get_kb_entries,
    DEFAULT_MODEL,
)


def get_demo_meta() -> DemoMetaResponse:
    kb_rows = len(get_kb_entries())
    dify_app_key = os.getenv("DIFY_APP_API_KEY", "").strip()
    return DemoMetaResponse(
        app_version=APP_VERSION,
        chat_lane_lab="Dify 正式知识库工作流" if dify_app_key else "Dify 未配置，当前处于结构化回退模式",
        chat_lane_agent="OpenAI 兼容直连",
        acceptance_status="已封版",
        formal_eval_score=FORMAL_EVAL_SCORE,
        stability_status=STABILITY_EVIDENCE,
        knowledge_base_rows=kb_rows,
        knowledge_base_imported=KB_IMPORT_SUCCESS_COUNT,
        demo_port=os.getenv("DEMO_PORT", "8088").strip() or "8088",
        runtime_model=os.getenv("OPENAI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
    )
