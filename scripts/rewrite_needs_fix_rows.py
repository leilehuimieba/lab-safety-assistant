#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import ai_review_kb as ark


REWRITE_FIELDS = [
    "answer",
    "steps",
    "ppe",
    "forbidden",
    "disposal",
    "first_aid",
    "emergency",
    "references",
]


def detect_language(text: str) -> str:
    value = (text or "").strip()
    if not value:
        return ""
    zh_count = sum(1 for ch in value if "\u4e00" <= ch <= "\u9fff")
    ascii_count = sum(1 for ch in value if ch.isascii() and ch.isalpha())
    if zh_count >= 20 or (zh_count > 0 and zh_count >= ascii_count // 2):
        return "zh-CN"
    return "en-US"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rewrite needs_fix/reject rows using AI.")
    parser.add_argument("--input-csv", required=True, help="Original candidate KB CSV.")
    parser.add_argument("--review-csv", required=True, help="ai_review_audit.csv path.")
    parser.add_argument("--output-csv", required=True, help="Rewritten KB CSV path.")
    parser.add_argument("--log-csv", required=True, help="Rewrite log CSV path.")
    parser.add_argument(
        "--openai-base-url",
        default="http://ai.little100.cn:3000/v1",
        help="OpenAI-compatible base URL.",
    )
    parser.add_argument("--openai-api-key", default="", help="OpenAI-compatible API key.")
    parser.add_argument("--openai-model", default="gpt-5.2-codex", help="Primary model.")
    parser.add_argument(
        "--openai-api",
        default="auto",
        help="API mode: auto | chat-completions | responses | openai-responses",
    )
    parser.add_argument(
        "--openai-fallback-models",
        default="grok-3-mini,grok-4,grok-3",
        help="Fallback models.",
    )
    parser.add_argument("--openai-timeout", type=float, default=60.0, help="Timeout seconds.")
    parser.add_argument("--openai-insecure-tls", action="store_true", help="Disable TLS verify.")
    parser.add_argument("--temperature", type=float, default=0.2, help="Rewrite temperature.")
    parser.add_argument("--limit", type=int, default=0, help="Optional target rewrite limit.")
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_kb_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ark.KB_FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in ark.KB_FIELDNAMES})


def write_log_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "id",
        "rewritten",
        "used_model",
        "error",
        "changed_fields",
        "before_decision",
        "before_score",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def now_date() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def extract_json_object(raw_text: str) -> dict[str, Any]:
    candidate = ark.extract_first_json_object(raw_text)
    if not candidate:
        return {}
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def ensure_minimum_fields(row: dict[str, str]) -> None:
    question = (row.get("question") or row.get("scenario") or "").strip()
    if len((row.get("answer") or "").strip()) < 80:
        row["answer"] = (
            "根据该条目对应的规范要求，实验室应落实风险辨识、分级分类管理、人员培训准入、"
            "隐患排查闭环和应急处置准备。执行时应结合本单位制度与现场条件制定可操作SOP。"
        )
        if question:
            row["answer"] = f"{row['answer']}（对应问题：{question}）"

    if not (row.get("steps") or "").strip():
        row["steps"] = (
            "1) 识别危险源并完成风险评估；"
            "2) 明确责任人并执行培训准入；"
            "3) 开展日常检查与隐患整改闭环；"
            "4) 定期演练应急预案并复盘。"
        )
    if not (row.get("ppe") or "").strip():
        row["ppe"] = "按实验风险配备并正确使用实验服、护目镜、防护手套和必要呼吸防护。"
    if not (row.get("forbidden") or "").strip():
        row["forbidden"] = "禁止未培训人员独立操作；禁止违规存放或混放危化品；禁止带故障设备运行。"
    if not (row.get("emergency") or "").strip():
        row["emergency"] = "发生异常立即停止实验、撤离并警戒，按预案报告并联系校内应急力量处置。"
    if not (row.get("disposal") or "").strip():
        row["disposal"] = "实验废弃物分类收集，按危废/生物废弃物制度交由有资质单位处置。"
    if not (row.get("first_aid") or "").strip():
        row["first_aid"] = "发生暴露或伤害后立即进行现场冲洗/止血等急救，并尽快转送医疗评估。"
    if not (row.get("references") or "").strip():
        source_title = (row.get("source_title") or row.get("title") or "").strip()
        source_url = (row.get("source_url") or "").strip()
        ref = source_title if source_title else "来源文档"
        if source_url:
            ref = f"{ref} | {source_url}"
        row["references"] = ref


def build_rewrite_prompts(kb_row: dict[str, str], review_row: dict[str, str]) -> tuple[str, str]:
    system_prompt = (
        "你是实验室安全知识库修订助手。"
        "请根据审核问题修复条目，输出仅 JSON 对象。"
        "必须包含以下键：answer,steps,ppe,forbidden,disposal,first_aid,emergency,references。"
        "要求：1) 使用中文；2) 直接可执行；3) 避免空字段；4) 禁止输出 markdown；"
        "5) 仅写可由来源支持或通用安全原则支持的内容；6) 不要编造硬性数值阈值与法律条款编号。"
    )
    payload = {
        "row": {
            "id": kb_row.get("id", ""),
            "title": kb_row.get("title", ""),
            "category": kb_row.get("category", ""),
            "lab_type": kb_row.get("lab_type", ""),
            "risk_level": kb_row.get("risk_level", ""),
            "question": kb_row.get("question", ""),
            "answer": kb_row.get("answer", ""),
            "steps": kb_row.get("steps", ""),
            "ppe": kb_row.get("ppe", ""),
            "forbidden": kb_row.get("forbidden", ""),
            "emergency": kb_row.get("emergency", ""),
            "references": kb_row.get("references", ""),
            "source_url": kb_row.get("source_url", ""),
        },
        "review_feedback": {
            "decision": review_row.get("ai_decision", ""),
            "score": review_row.get("ai_score", ""),
            "issues": review_row.get("ai_issues", ""),
            "post_rule": review_row.get("ai_post_rule", ""),
            "rewrite_suggestion": review_row.get("ai_rewrite_suggestion", ""),
        },
    }
    user_prompt = "请修复以下条目并返回 JSON：\n" + json.dumps(payload, ensure_ascii=False, indent=2)
    return system_prompt, user_prompt


def to_int(value: str, default: int = 0) -> int:
    try:
        return int(float((value or "").strip() or str(default)))
    except ValueError:
        return default


def main() -> int:
    args = parse_args()
    input_csv = Path(args.input_csv).resolve()
    review_csv = Path(args.review_csv).resolve()
    output_csv = Path(args.output_csv).resolve()
    log_csv = Path(args.log_csv).resolve()

    if not input_csv.exists():
        raise SystemExit(f"Input CSV not found: {input_csv}")
    if not review_csv.exists():
        raise SystemExit(f"Review CSV not found: {review_csv}")
    if not args.openai_api_key.strip():
        raise SystemExit("Missing API key. Set --openai-api-key or OPENAI_API_KEY.")

    kb_rows = read_csv(input_csv)
    review_rows = read_csv(review_csv)
    review_map = {row.get("id", "").strip(): row for row in review_rows if row.get("id", "").strip()}

    models = [args.openai_model.strip(), *ark.split_csv_tokens(args.openai_fallback_models)]
    unique_models: list[str] = []
    for model in models:
        if model and model not in unique_models:
            unique_models.append(model)

    endpoint = ark.resolve_endpoint(args.openai_base_url)
    logs: list[dict[str, str]] = []
    rewritten_count = 0
    attempted = 0

    for row in kb_rows:
        row_id = (row.get("id") or "").strip()
        review_row = review_map.get(row_id)
        if not review_row:
            logs.append(
                {
                    "id": row_id,
                    "rewritten": "no",
                    "used_model": "",
                    "error": "missing_review_row",
                    "changed_fields": "",
                    "before_decision": "",
                    "before_score": "",
                }
            )
            continue

        ai_pass = (review_row.get("ai_pass", "") or "").strip().lower()
        ai_decision = (review_row.get("ai_decision", "") or "").strip().lower()
        needs_rewrite = ai_pass != "yes" and ai_decision in {"needs_fix", "reject"}
        if not needs_rewrite:
            logs.append(
                {
                    "id": row_id,
                    "rewritten": "no",
                    "used_model": "",
                    "error": "",
                    "changed_fields": "",
                    "before_decision": review_row.get("ai_decision", ""),
                    "before_score": review_row.get("ai_score", ""),
                }
            )
            continue

        if args.limit > 0 and attempted >= args.limit:
            logs.append(
                {
                    "id": row_id,
                    "rewritten": "no",
                    "used_model": "",
                    "error": "rewrite_limit_reached",
                    "changed_fields": "",
                    "before_decision": review_row.get("ai_decision", ""),
                    "before_score": review_row.get("ai_score", ""),
                }
            )
            continue

        attempted += 1
        before = {field: row.get(field, "") for field in REWRITE_FIELDS}
        system_prompt, user_prompt = build_rewrite_prompts(row, review_row)
        raw_text, used_model, call_error = ark.call_model(
            endpoint=endpoint,
            api_key=args.openai_api_key.strip(),
            models=unique_models,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=args.temperature,
            timeout=args.openai_timeout,
            insecure_tls=args.openai_insecure_tls,
            api_mode=args.openai_api,
        )

        payload = extract_json_object(raw_text) if not call_error else {}
        parse_error = "" if payload else ("missing_or_invalid_rewrite_json" if not call_error else call_error)

        if payload:
            for field in REWRITE_FIELDS:
                value = payload.get(field)
                if isinstance(value, str) and value.strip():
                    row[field] = value.strip()
                elif isinstance(value, list):
                    row[field] = "; ".join(str(item).strip() for item in value if str(item).strip())

        ensure_minimum_fields(row)
        merged_text = f"{row.get('answer', '')}\n{row.get('steps', '')}\n{row.get('question', '')}"
        detected = detect_language(merged_text)
        if detected:
            row["language"] = detected
        row["reviewer"] = f"ai-rewrite:{used_model or args.openai_model}"
        row["status"] = "ai_rewritten"
        row["last_updated"] = now_date()
        legal_notes = (row.get("legal_notes") or "").strip()
        rewrite_note = f"[AI rewrite attempt decision={review_row.get('ai_decision','')} score={review_row.get('ai_score','')}]"
        row["legal_notes"] = f"{legal_notes} {rewrite_note}".strip()

        changed = [field for field in REWRITE_FIELDS if (before.get(field, "") or "").strip() != (row.get(field, "") or "").strip()]
        rewritten = "yes" if changed else "no"
        if rewritten == "yes":
            rewritten_count += 1

        logs.append(
            {
                "id": row_id,
                "rewritten": rewritten,
                "used_model": used_model or args.openai_model,
                "error": parse_error,
                "changed_fields": ";".join(changed),
                "before_decision": review_row.get("ai_decision", ""),
                "before_score": review_row.get("ai_score", ""),
            }
        )

    # Ensure high-risk rows are complete after rewriting.
    for row in kb_rows:
        if to_int(row.get("risk_level", "0")) >= 4:
            ensure_minimum_fields(row)

    write_kb_csv(output_csv, kb_rows)
    write_log_csv(log_csv, logs)

    failed = sum(1 for item in logs if item.get("error"))
    print("Rewrite completed:")
    print(f"- input rows: {len(kb_rows)}")
    print(f"- attempted rewrites: {attempted}")
    print(f"- rewritten rows: {rewritten_count}")
    print(f"- rewrite errors: {failed}")
    print(f"- output csv: {output_csv}")
    print(f"- log csv: {log_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
