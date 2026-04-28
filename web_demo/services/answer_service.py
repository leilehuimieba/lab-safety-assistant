from __future__ import annotations

"""答案构建与低置信度处理服务

- assess_low_confidence: 根据引用分数判断是否为低置信度查询
- append_low_confidence_followup: 将低置信度问题写入待补强队列 CSV
- build_rule_answer: 按匹配规则生成标准化安全回答
- build_fallback_lab_answer: 在上游服务不可用时生成结构化回退回答
- append_low_confidence_followup_notice: 在回答末尾追加低置信度提示附注
"""

import csv
import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from ..models import Citation
from ..repositories import (
    DEFAULT_LOW_CONFIDENCE_TOP_SCORE,
    RISK_LABEL,
    QUEUE_HEADERS,
    LOW_CONFIDENCE_QUEUE_FILE,
    normalize_search_text,
    safe_read_csv_rows,
    write_csv_row,
    _QUEUE_LOCK,
)


def assess_low_confidence(citations: list[Citation]) -> tuple[bool, str]:
    if not citations:
        return True, "no_kb_match"
    threshold = float(os.getenv("LOW_CONFIDENCE_TOP_SCORE", str(DEFAULT_LOW_CONFIDENCE_TOP_SCORE)))
    if citations[0].score < threshold:
        return True, f"top_score_below_threshold:{citations[0].score}<{threshold}"
    return False, ""


def append_low_confidence_followup(
    *,
    question: str,
    mode: str,
    decision: str,
    risk_level: str,
    matched_rule_id: str,
    matched_rule_action: str,
    low_confidence_reason: str,
    citations: list[Citation],
    queue_file: Path = LOW_CONFIDENCE_QUEUE_FILE,
) -> bool:
    question_norm = normalize_search_text(question)
    if not question_norm:
        return False
    question_hash = hashlib.sha1(question_norm.encode("utf-8")).hexdigest()
    queue_file.parent.mkdir(parents=True, exist_ok=True)

    with _QUEUE_LOCK:
        existing_hashes: set[str] = set()
        if queue_file.exists():
            with queue_file.open("r", encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    value = (row.get("question_hash") or "").strip()
                    if value:
                        existing_hashes.add(value)
        if question_hash in existing_hashes:
            return False

        top = citations[0] if citations else None
        write_csv_row(
            queue_file,
            QUEUE_HEADERS,
            {
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "question_hash": question_hash,
                "question": question.strip(),
                "mode": mode,
                "decision": decision,
                "risk_level": risk_level,
                "matched_rule_id": matched_rule_id,
                "matched_rule_action": matched_rule_action,
                "low_confidence_reason": low_confidence_reason,
                "citation_count": str(len(citations)),
                "top_score": str(top.score if top else ""),
                "top_kb_id": top.kb_id if top else "",
                "top_source_title": top.source_title if top else "",
                "suggested_lane": "collector",
                "suggested_action": "add_or_rewrite_kb_entry",
                "status": "open",
                "notes": "",
            },
        )
    return True


def format_citation_lines(citations: list[Citation], limit: int = 3) -> str:
    if not citations:
        return "- no direct KB citation"
    return "\n".join(f"- {item.kb_id}: {item.source_title or item.title or '-'}" for item in citations[:limit])


def build_rule_answer(rule: dict[str, Any], citations: list[Citation]) -> str:
    response = str(rule.get("response") or "Stop the task and follow the local emergency procedure immediately.").strip()
    return (
        "结论:\n"
        f"{response}\n\n"
        "步骤:\n"
        "1. 立即停止当前操作并隔离危险源。\n"
        "2. 第一时间通知实验室负责人和安全联系人。\n"
        "3. 按本单位 SOP 执行现场控制、上报和记录。\n\n"
        "禁止事项:\n"
        "- 禁止继续开展当前高风险操作。\n"
        "- 禁止绕过通风、审批、联锁或 PPE 要求。\n\n"
        "应急升级:\n"
        "- 如存在受伤、起火、泄漏或暴露风险，立即启动应急预案。\n\n"
        "参考依据:\n"
        f"{format_citation_lines(citations)}"
    )


def build_fallback_lab_answer(
    question: str,
    citations: list[Citation],
    rule: dict[str, Any] | None = None,
    low_confidence_reason: str = "",
) -> str:
    highest_risk = max(
        [int(float(item.risk_level)) for item in citations if str(item.risk_level).replace(".", "", 1).isdigit()] or [3]
    )
    risk_text = RISK_LABEL.get(highest_risk, "Medium")
    top_title = citations[0].title if citations else "No direct KB match"
    notes = low_confidence_reason or "upstream unavailable"
    guard = str((rule or {}).get("response") or "").strip()
    return (
        "结论:\n"
        f"请将该问题视为 {risk_text} 风险等级的实验室安全场景，优先依照本地 SOP 处理，不要临场 improvising。\n\n"
        "步骤:\n"
        "1. 先暂停操作并隔离能量、反应或暴露源。\n"
        "2. 重新核对 PPE、围护、通风和应急设备状态。\n"
        "3. 按书面 SOP 执行，并明确一人控制、一人观察、一人上报。\n"
        "4. 如已出现受伤、起火、泄漏或异常反应，立即启动应急预案。\n\n"
        "禁止事项:\n"
        "- 未经授权或无人监护时禁止继续操作。\n"
        "- 禁止绕过通风、断电锁定、屏蔽或废弃物分类要求。\n"
        "- 禁止隐瞒异常情况或延迟上报。\n\n"
        "应急升级:\n"
        "- 人员受伤或暴露：先冲洗或隔离，再联系医疗支持。\n"
        "- 存在起火或爆炸风险：立即撤离并联系应急力量。\n"
        "- 存在泄漏：先警戒隔离，再按泄漏 SOP 处置。\n\n"
        "参考依据:\n"
        f"- top context: {top_title}\n"
        f"{format_citation_lines(citations)}\n\n"
        "备注:\n"
        f"- fallback reason: {notes}\n"
        f"- guardrail: {guard or 'N/A'}\n"
        f"- original question: {question.strip()}"
    )


def append_low_confidence_followup_notice(answer: str) -> str:
    note = "附注：该问题已加入低置信待补强队列，后续会继续完善知识库。"
    text = (answer or "").strip()
    if not text or note in text:
        return text or note
    return f"{text}\n\n{note}"
