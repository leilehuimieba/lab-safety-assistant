"""LabSafe Assistant — 业务逻辑服务层

此包存放 web_demo 的业务逻辑，已从单文件 core.py 按业务域拆分为：
- kb_service.py: 知识库检索与规则匹配
- answer_service.py: 答案构建与低置信度处理
- llm_output_service.py: LLM 输出清洗与乱码修复
- upstream_service.py: Dify 与 OpenAI 兼容上游调用
- emergency_service.py: 应急卡片匹配
- meta_service.py: 应用元信息
- risk_service.py: 风险评估、检查清单生成与提交
- training_service.py: 培训题库、考核评分与统计
- incident_service.py: 事故记录 CRUD 与复盘分析
- dashboard_service.py: 管理仪表盘、工作区状态、周报与导出
"""

from .kb_service import (
    retrieve_citations,
    match_rule,
    should_enforce_terminal_rule,
)
from .answer_service import (
    assess_low_confidence,
    append_low_confidence_followup,
    format_citation_lines,
    build_rule_answer,
    build_fallback_lab_answer,
    append_low_confidence_followup_notice,
)
from .llm_output_service import (
    fix_mojibake_text,
    sanitize_llm_output,
)
from .upstream_service import (
    iter_sse_payloads,
    parse_sse_answer,
    resolve_dify_api_base,
    build_dify_proxy_auth,
    call_dify_lab,
    parse_openai_compat_sse,
    build_system_prompt,
    build_user_message,
    call_upstream,
)
from .emergency_service import (
    to_emergency_card,
    match_emergency_card,
)
from .meta_service import (
    get_demo_meta,
)
from .risk_service import (
    build_checklist_template,
    build_risk_assessment,
    dedupe_checklist_items,
    evaluate_checklist_submission,
    filter_checklist_rows,
)
from .training_service import (
    get_training_questions,
    grade_training_submit,
    load_training_stats,
    to_public_question,
)
from .incident_service import (
    compute_incident_due_state,
    compute_incident_recurrence_risk,
    create_incident_record,
    load_incident_records,
    parse_json_list_field,
    update_incident_record,
    write_incident_records,
)
from .dashboard_service import (
    build_weekly_report_markdown,
    build_workspace_status,
    export_rows_to_csv,
    load_admin_dashboard,
    summarize_top_values,
)
