#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

CHECKLIST_HEADERS = [
    "record_id",
    "submitted_at",
    "operator",
    "scenario",
    "risk_score",
    "risk_level",
    "key_hazards",
    "allow_start",
    "blocking_reasons",
    "items_json",
    "notes",
]

TRAINING_ATTEMPT_HEADERS = [
    "attempt_id",
    "submitted_at",
    "participant",
    "session_id",
    "score",
    "total_questions",
    "pass_threshold",
    "passed",
    "weak_categories",
]

TRAINING_MISTAKE_HEADERS = [
    "attempt_id",
    "submitted_at",
    "participant",
    "session_id",
    "question_id",
    "category",
    "prompt",
    "selected_indices",
    "correct_indices",
    "references",
]

INCIDENT_HEADERS = [
    "incident_id",
    "reported_at",
    "updated_at",
    "reporter",
    "title",
    "scenario",
    "severity",
    "status",
    "location",
    "cause_categories",
    "immediate_actions",
    "corrective_actions",
    "owner",
    "due_date",
    "closure_notes",
]

QUEUE_HEADERS = [
    "created_at",
    "question_hash",
    "question",
    "mode",
    "decision",
    "risk_level",
    "matched_rule_id",
    "matched_rule_action",
    "low_confidence_reason",
    "citation_count",
    "top_score",
    "top_kb_id",
    "top_source_title",
    "suggested_lane",
    "suggested_action",
    "status",
    "notes",
]


def write_csv(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    now = datetime.now()
    dt = lambda delta: (now + delta).isoformat(timespec="seconds")
    d = lambda delta_days: (now + timedelta(days=delta_days)).date().isoformat()

    checklist_rows = [
        {
            "record_id": "CHK-DEMO-001",
            "submitted_at": dt(timedelta(hours=-2)),
            "operator": "答辩演示账号",
            "scenario": "夜间在通风柜内进行乙醇回流，并计划临时更换冷凝管继续加热。",
            "risk_score": "4",
            "risk_level": "High",
            "key_hazards": "Chemical|Fire",
            "allow_start": "false",
            "blocking_reasons": "Supervisor approval or buddy check is completed for this high-risk operation. | The task is not being performed alone or an approved escalation path is active.",
            "items_json": json.dumps(
                [
                    {"id": "sop_reviewed", "label": "SOP, SDS, and experiment objective have been reviewed.", "critical": True, "checked": True, "note": ""},
                    {"id": "label_verified", "label": "Reagent names, concentrations, and labels have been double-checked.", "critical": True, "checked": True, "note": ""},
                    {"id": "ppe_ready", "label": "Required PPE is available, correctly worn, and suitable for this task.", "critical": True, "checked": True, "note": ""},
                    {"id": "containment_ready", "label": "Ventilation, shielding, or containment controls are available and working.", "critical": True, "checked": True, "note": ""},
                    {"id": "emergency_ready", "label": "Emergency shower, eyewash, extinguisher, exits, and contacts are confirmed.", "critical": True, "checked": True, "note": ""},
                    {"id": "high_risk_authorized", "label": "Supervisor approval or buddy check is completed for this high-risk operation.", "critical": True, "checked": False, "note": "审批单未补签"},
                    {"id": "working_alone_control", "label": "The task is not being performed alone or an approved escalation path is active.", "critical": True, "checked": False, "note": "现场仅一人值守"},
                ],
                ensure_ascii=False,
            ),
            "notes": "用于演示开工前阻断逻辑，故意保留审批和监护缺口。",
        }
    ]

    training_attempt_rows = [
        {
            "attempt_id": "TRN-DEMO-001",
            "submitted_at": dt(timedelta(hours=-1, minutes=-20)),
            "participant": "答辩演示账号",
            "session_id": "SESSION-DEMO-001",
            "score": "80",
            "total_questions": "5",
            "pass_threshold": "80",
            "passed": "true",
            "weak_categories": "Emergency",
        }
    ]

    training_mistake_rows = [
        {
            "attempt_id": "TRN-DEMO-001",
            "submitted_at": dt(timedelta(hours=-1, minutes=-20)),
            "participant": "答辩演示账号",
            "session_id": "SESSION-DEMO-001",
            "question_id": "Q008",
            "category": "Emergency",
            "prompt": "After chemical exposure to the eyes, which statement is correct?",
            "selected_indices": json.dumps([0], ensure_ascii=False),
            "correct_indices": json.dumps([1], ensure_ascii=False),
            "references": "Eyewash SOP | SDS Section 4",
        }
    ]

    incident_rows = [
        {
            "incident_id": "INC-DEMO-001",
            "reported_at": dt(timedelta(days=-1, hours=-3)),
            "updated_at": dt(timedelta(hours=-4)),
            "reporter": "答辩演示账号",
            "title": "乙醇回流前发现审批缺失与监护不足",
            "scenario": "夜间准备开展乙醇回流实验时，检查发现高风险审批未闭环，且现场只有一名学生值守，未满足双人监护要求，实验被系统阻断。",
            "severity": "high",
            "status": "action_in_progress",
            "location": "化学实验楼 A302",
            "cause_categories": json.dumps(["审批流程未闭环", "单人作业风险", "开工前复核不足"], ensure_ascii=False),
            "immediate_actions": json.dumps(
                ["停止开工", "联系导师补审", "安排第二名监护人员到场"], ensure_ascii=False
            ),
            "corrective_actions": json.dumps(
                ["将高风险审批单纳入开工前必查项", "夜间高风险实验默认双人到场", "每周抽查审批与监护记录"], ensure_ascii=False
            ),
            "owner": "实验室管理员",
            "due_date": d(-1),
            "closure_notes": "",
        }
    ]

    low_conf_rows = [
        {
            "created_at": dt(timedelta(hours=-6)),
            "question_hash": "demo-lowconf-001",
            "question": "高风险实验审批通过后还要不要双人复核？",
            "mode": "lab",
            "decision": "llm_low_confidence",
            "risk_level": "high",
            "matched_rule_id": "",
            "matched_rule_action": "",
            "low_confidence_reason": "",
            "citation_count": "1",
            "top_score": "2.8",
            "top_kb_id": "KB-1054",
            "top_source_title": "高等学校实验室安全规范",
            "suggested_lane": "collector",
            "suggested_action": "verify_demo_question",
            "status": "open",
            "notes": "用于演示低置信问题回流机制",
        },
        {
            "created_at": dt(timedelta(hours=-5)),
            "question_hash": "demo-lowconf-002",
            "question": "培训没通过可以独立进行高风险实验吗？",
            "mode": "lab",
            "decision": "llm_low_confidence",
            "risk_level": "high",
            "matched_rule_id": "",
            "matched_rule_action": "",
            "low_confidence_reason": "",
            "citation_count": "1",
            "top_score": "2.6",
            "top_kb_id": "KB-1057",
            "top_source_title": "高等学校实验室安全规范",
            "suggested_lane": "cleaner",
            "suggested_action": "add_grounding_and_eval_case",
            "status": "open",
            "notes": "用于演示知识补强任务沉淀",
        },
    ]

    write_csv(repo_root / "artifacts" / "checklists" / "checklist_runs.csv", CHECKLIST_HEADERS, checklist_rows)
    write_csv(repo_root / "artifacts" / "training" / "training_attempts.csv", TRAINING_ATTEMPT_HEADERS, training_attempt_rows)
    write_csv(repo_root / "artifacts" / "training" / "training_mistakes.csv", TRAINING_MISTAKE_HEADERS, training_mistake_rows)
    write_csv(repo_root / "artifacts" / "incidents" / "incident_reviews.csv", INCIDENT_HEADERS, incident_rows)
    write_csv(repo_root / "artifacts" / "low_confidence_followups" / "data_gap_queue.csv", QUEUE_HEADERS, low_conf_rows)

    print("seeded fixed demo data:")
    print("- checklist_runs.csv: 1 blocked record")
    print("- training_attempts.csv: 1 passing record")
    print("- training_mistakes.csv: 1 weak-category record")
    print("- incident_reviews.csv: 1 overdue action_in_progress record")
    print("- data_gap_queue.csv: 2 demo follow-up items")


if __name__ == "__main__":
    main()
