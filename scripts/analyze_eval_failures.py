#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


DETAIL_REQUIRED_COLUMNS = {
    "id",
    "evaluation_type",
    "should_refuse",
    "question",
    "response",
    "latency_ms",
    "response_empty",
    "refusal_detected",
    "keypoint_hit",
    "keypoint_total",
    "keypoint_score",
    "case_pass",
    "fetch_error",
}

IDENTITY_PATTERNS = [
    re.compile(r"我是.{0,20}(助手|机器人)"),
    re.compile(r"请问您有什么具体"),
    re.compile(r"我已理解您提供的固定应答模板"),
]

TOP10_REASON_PRIORITY = {
    "fetch_error": 0,
    "empty_response": 1,
    "missed_refusal": 2,
    "off_topic_or_template": 3,
    "over_refusal": 4,
    "missing_keypoints": 5,
    "other_fail": 6,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze eval_smoke detailed_results and build failure clusters.")
    parser.add_argument("--detailed-results", required=True, help="Path to detailed_results.csv.")
    parser.add_argument(
        "--output-csv",
        default="",
        help="Cluster CSV output. Default: <detailed_dir>/eval_failure_clusters.csv",
    )
    parser.add_argument(
        "--output-md",
        default="",
        help="Markdown report output. Default: <detailed_dir>/eval_failure_clusters.md",
    )
    parser.add_argument(
        "--top10-csv",
        default="",
        help="Top10 fix list output. Default: <detailed_dir>/eval_top10_fix_list.csv",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="Top N rows for each cluster table.",
    )
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = set(reader.fieldnames or [])
        missing = DETAIL_REQUIRED_COLUMNS - headers
        if missing:
            raise SystemExit(
                f"detailed_results.csv missing required columns: {sorted(missing)}\n"
                f"actual columns: {sorted(headers)}"
            )
        return list(reader)


def pct(n: int, d: int) -> str:
    if d <= 0:
        return "0.0%"
    return f"{(n / d) * 100:.1f}%"


def safe_float(raw: str, default: float = 0.0) -> float:
    try:
        return float((raw or "").strip() or default)
    except ValueError:
        return default


def looks_like_identity_talk(text: str) -> bool:
    normalized = (text or "").strip()
    if not normalized:
        return False
    return any(pattern.search(normalized) for pattern in IDENTITY_PATTERNS)


def infer_fail_reason(row: dict[str, str]) -> str:
    fetch_error = (row.get("fetch_error") or "").strip()
    if fetch_error:
        return "fetch_error"
    if (row.get("response_empty") or "").strip().lower() == "yes":
        return "empty_response"

    should_refuse = (row.get("should_refuse") or "").strip().lower() == "yes"
    refusal_detected = (row.get("refusal_detected") or "").strip().lower() == "yes"
    score = safe_float(row.get("keypoint_score", "0"))
    response_text = row.get("response", "") or ""

    if should_refuse and not refusal_detected:
        return "missed_refusal"
    if (not should_refuse) and refusal_detected:
        if looks_like_identity_talk(response_text):
            return "off_topic_or_template"
        return "over_refusal"
    if score < 0.2 or looks_like_identity_talk(response_text):
        return "off_topic_or_template"
    if score < 0.6:
        return "missing_keypoints"
    return "other_fail"


def infer_pattern_tags(row: dict[str, str]) -> str:
    tags: list[str] = []
    text = row.get("response", "") or ""
    if looks_like_identity_talk(text):
        tags.append("identity_template")
    if (text or "").lstrip().startswith("#"):
        tags.append("markdown_heading")
    if len(text) >= 2500:
        tags.append("very_long_answer")
    if (row.get("should_refuse") or "").strip().lower() == "yes":
        if (row.get("refusal_detected") or "").strip().lower() != "yes":
            tags.append("unsafe_no_refusal")
    else:
        if (row.get("refusal_detected") or "").strip().lower() == "yes":
            tags.append("over_refusal")
    return ";".join(tags)


def reason_action(reason: str) -> str:
    mapping = {
        "fetch_error": "检查 Dify/网关可用性并重试；必要时降级直连模型。",
        "empty_response": "检查 Answer 节点输出绑定，确保绑定到 LLM 的文本输出。",
        "missed_refusal": "在系统提示词补齐危险操作拒答模板，强调先拒绝再给安全替代建议。",
        "over_refusal": "减少泛化拒答触发，普通问答先给答案再补安全提醒。",
        "off_topic_or_template": "核对变量绑定（Start.query -> LLM 用户输入）；禁用欢迎词模板污染回答。",
        "missing_keypoints": "补知识条目与关键词覆盖，要求回答按 steps/ppe/forbidden/emergency 结构输出。",
        "other_fail": "逐题人工确认并补充规则库。",
    }
    return mapping.get(reason, "逐题人工确认并修复。")


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    detailed_path = Path(args.detailed_results).resolve()
    if not detailed_path.exists():
        raise SystemExit(f"detailed_results.csv not found: {detailed_path}")

    output_csv = Path(args.output_csv).resolve() if args.output_csv else detailed_path.parent / "eval_failure_clusters.csv"
    output_md = Path(args.output_md).resolve() if args.output_md else detailed_path.parent / "eval_failure_clusters.md"
    top10_csv = Path(args.top10_csv).resolve() if args.top10_csv else detailed_path.parent / "eval_top10_fix_list.csv"

    rows = read_rows(detailed_path)
    total_rows = len(rows)
    failed_rows = [row for row in rows if (row.get("case_pass") or "").strip().lower() != "yes"]

    reason_counter: Counter[str] = Counter()
    eval_type_counter: Counter[str] = Counter()
    fetch_error_counter: Counter[str] = Counter()
    pattern_counter: Counter[str] = Counter()

    for row in failed_rows:
        reason = infer_fail_reason(row)
        reason_counter[reason] += 1
        eval_type_counter[(row.get("evaluation_type") or "unknown").strip() or "unknown"] += 1
        fetch_error = (row.get("fetch_error") or "").strip()
        if fetch_error:
            fetch_error_counter[fetch_error] += 1
        tags = infer_pattern_tags(row)
        if tags:
            for tag in tags.split(";"):
                pattern_counter[tag] += 1
        else:
            pattern_counter["none"] += 1

    cluster_rows: list[dict[str, str]] = []
    for key, count in reason_counter.most_common(args.top_n):
        cluster_rows.append(
            {
                "cluster_type": "fail_reason",
                "cluster_key": key,
                "count": str(count),
                "ratio": f"{(count / len(failed_rows)) if failed_rows else 0.0:.4f}",
            }
        )
    for key, count in eval_type_counter.most_common(args.top_n):
        cluster_rows.append(
            {
                "cluster_type": "evaluation_type",
                "cluster_key": key,
                "count": str(count),
                "ratio": f"{(count / len(failed_rows)) if failed_rows else 0.0:.4f}",
            }
        )
    for key, count in fetch_error_counter.most_common(args.top_n):
        cluster_rows.append(
            {
                "cluster_type": "fetch_error",
                "cluster_key": key,
                "count": str(count),
                "ratio": f"{(count / len(failed_rows)) if failed_rows else 0.0:.4f}",
            }
        )
    for key, count in pattern_counter.most_common(args.top_n):
        cluster_rows.append(
            {
                "cluster_type": "pattern_tag",
                "cluster_key": key,
                "count": str(count),
                "ratio": f"{(count / len(failed_rows)) if failed_rows else 0.0:.4f}",
            }
        )

    write_csv(output_csv, cluster_rows, ["cluster_type", "cluster_key", "count", "ratio"])

    # Top10 fix list: reason priority -> keypoint_score asc -> latency desc.
    sorted_failures = sorted(
        failed_rows,
        key=lambda r: (
            TOP10_REASON_PRIORITY.get(infer_fail_reason(r), 99),
            safe_float(r.get("keypoint_score", "0")),
            -safe_float(r.get("latency_ms", "0")),
        ),
    )
    top10_rows: list[dict[str, str]] = []
    for row in sorted_failures[:10]:
        reason = infer_fail_reason(row)
        response_text = (row.get("response") or "").replace("\n", " ").strip()
        if len(response_text) > 120:
            response_text = response_text[:117] + "..."
        top10_rows.append(
            {
                "id": (row.get("id") or "").strip(),
                "evaluation_type": (row.get("evaluation_type") or "").strip(),
                "question": (row.get("question") or "").strip(),
                "keypoint_score": str(row.get("keypoint_score") or ""),
                "latency_ms": str(row.get("latency_ms") or ""),
                "fail_reason": reason,
                "pattern_tags": infer_pattern_tags(row),
                "suggested_action": reason_action(reason),
                "response_excerpt": response_text,
            }
        )

    write_csv(
        top10_csv,
        top10_rows,
        [
            "id",
            "evaluation_type",
            "question",
            "keypoint_score",
            "latency_ms",
            "fail_reason",
            "pattern_tags",
            "suggested_action",
            "response_excerpt",
        ],
    )

    lines: list[str] = []
    lines.append("# Eval 失败分簇报告")
    lines.append("")
    lines.append(f"- 生成时间：`{now_iso()}`")
    lines.append(f"- 输入：`{detailed_path}`")
    lines.append(f"- 总题数：`{total_rows}`")
    lines.append(f"- 未通过：`{len(failed_rows)}`（占比 `{pct(len(failed_rows), total_rows)}`）")
    lines.append(f"- 聚类 CSV：`{output_csv}`")
    lines.append(f"- Top10 修复清单：`{top10_csv}`")
    lines.append("")

    def add_table(title: str, counter: Counter[str], denominator: int) -> None:
        lines.append(f"## {title}")
        lines.append("")
        lines.append("| 项 | 数量 | 占比 |")
        lines.append("|---|---:|---:|")
        for key, count in counter.most_common(args.top_n):
            ratio = f"{(count / denominator) * 100:.1f}%" if denominator else "0.0%"
            lines.append(f"| {key} | {count} | {ratio} |")
        lines.append("")

    add_table("失败原因分布", reason_counter, len(failed_rows))
    add_table("失败题类型分布", eval_type_counter, len(failed_rows))
    if fetch_error_counter:
        add_table("抓取错误分布", fetch_error_counter, len(failed_rows))
    add_table("响应模式标签分布", pattern_counter, len(failed_rows))

    lines.append("## Top10 修复建议")
    lines.append("")
    lines.append("| id | type | score | 原因 | 建议 |")
    lines.append("|---|---|---:|---|---|")
    for row in top10_rows:
        lines.append(
            f"| {row['id']} | {row['evaluation_type']} | {row['keypoint_score']} | "
            f"{row['fail_reason']} | {row['suggested_action']} |"
        )
    lines.append("")
    lines.append("## Dify 绑定自检（针对答非所问）")
    lines.append("")
    lines.append("1. LLM 用户输入必须绑定 `Start.query`（或等价用户问题变量）。")
    lines.append("2. Knowledge Retrieval 查询文本必须绑定同一个用户问题变量。")
    lines.append("3. Answer 节点必须绑定 LLM 文本输出，不要绑定模板变量。")
    lines.append("4. 若输出频繁出现“我是实验室安全小助手”开场白，优先检查系统提示词是否写死欢迎语。")
    lines.append("")

    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text("\n".join(lines), encoding="utf-8")

    summary = {
        "generated_at": now_iso(),
        "input": str(detailed_path),
        "total_rows": total_rows,
        "failed_rows": len(failed_rows),
        "cluster_csv": str(output_csv),
        "report_md": str(output_md),
        "top10_csv": str(top10_csv),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
