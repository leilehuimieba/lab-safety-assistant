#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze ai_review CSV and generate failure clusters.")
    parser.add_argument("--input-csv", required=True, help="Path to ai_review_*.csv.")
    parser.add_argument(
        "--output-csv",
        default="",
        help="Path to output cluster CSV. Default: <input_dir>/failure_clusters.csv",
    )
    parser.add_argument(
        "--output-md",
        default="",
        help="Path to output markdown report. Default: <input_dir>/failure_clusters.md",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=15,
        help="Top N items per cluster dimension.",
    )
    return parser.parse_args()


def split_multi(text: str) -> list[str]:
    raw = (text or "").strip()
    if not raw:
        return []
    parts = re.split(r"[;；\n]+", raw)
    return [item.strip() for item in parts if item.strip()]


def classify_error(error_text: str) -> str:
    text = (error_text or "").strip().lower()
    if not text:
        return "none"
    if "cert" in text and "verify" in text:
        return "tls_cert_error"
    if "http_404" in text:
        return "http_404"
    if "http_401" in text or "http_403" in text:
        return "auth_or_forbidden"
    if "http_429" in text:
        return "rate_limited"
    if "http_5" in text:
        return "upstream_5xx"
    if "timeout" in text:
        return "timeout"
    if "request_error" in text:
        return "request_error"
    if "invalid_json" in text or "missing_json_object" in text:
        return "parse_error"
    return "other_error"


def score_bucket(score_raw: str) -> str:
    try:
        score = int(float((score_raw or "0").strip() or "0"))
    except ValueError:
        score = 0
    if score < 30:
        return "00-29"
    if score < 50:
        return "30-49"
    if score < 70:
        return "50-69"
    if score < 85:
        return "70-84"
    return "85-100"


def top_counter_rows(cluster_type: str, counter: Counter[str], total: int, top_n: int) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for key, count in counter.most_common(top_n):
        ratio = (count / total) if total else 0.0
        rows.append(
            {
                "cluster_type": cluster_type,
                "cluster_key": key,
                "count": str(count),
                "ratio": f"{ratio:.4f}",
            }
        )
    return rows


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = ["cluster_type", "cluster_key", "count", "ratio"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def main() -> int:
    args = parse_args()
    input_csv = Path(args.input_csv).resolve()
    if not input_csv.exists():
        raise SystemExit(f"Input CSV not found: {input_csv}")

    output_csv = Path(args.output_csv).resolve() if args.output_csv else input_csv.parent / "failure_clusters.csv"
    output_md = Path(args.output_md).resolve() if args.output_md else input_csv.parent / "failure_clusters.md"
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)

    rows = read_rows(input_csv)
    total = len(rows)
    blocked_rows = [row for row in rows if (row.get("ai_pass", "").strip().lower() != "yes")]
    blocked_total = len(blocked_rows)

    decision_counter: Counter[str] = Counter()
    score_bucket_counter: Counter[str] = Counter()
    error_counter: Counter[str] = Counter()
    post_rule_counter: Counter[str] = Counter()
    issue_counter: Counter[str] = Counter()

    for row in blocked_rows:
        decision_counter[(row.get("ai_decision") or "unknown").strip() or "unknown"] += 1
        score_bucket_counter[score_bucket(row.get("ai_score", ""))] += 1
        error_counter[classify_error(row.get("ai_error", ""))] += 1

        post_rules = split_multi(row.get("ai_post_rule", ""))
        if not post_rules:
            post_rule_counter["none"] += 1
        for item in post_rules:
            post_rule_counter[item] += 1

        issues = split_multi(row.get("ai_issues", ""))
        if not issues:
            issue_counter["none"] += 1
        for issue in issues:
            issue_counter[issue] += 1

    cluster_rows: list[dict[str, str]] = []
    cluster_rows.extend(top_counter_rows("decision", decision_counter, blocked_total, args.top_n))
    cluster_rows.extend(top_counter_rows("score_bucket", score_bucket_counter, blocked_total, args.top_n))
    cluster_rows.extend(top_counter_rows("error_type", error_counter, blocked_total, args.top_n))
    cluster_rows.extend(top_counter_rows("post_rule", post_rule_counter, blocked_total, args.top_n))
    cluster_rows.extend(top_counter_rows("issue", issue_counter, blocked_total, args.top_n))
    write_csv(output_csv, cluster_rows)

    low_score_rows = sorted(
        blocked_rows,
        key=lambda item: int(float((item.get("ai_score") or "0").strip() or "0")),
    )[: min(10, blocked_total)]

    md_lines: list[str] = []
    md_lines.append("# AI 低分原因聚类报告")
    md_lines.append("")
    md_lines.append(f"- 生成时间：`{now_iso()}`")
    md_lines.append(f"- 输入文件：`{input_csv}`")
    md_lines.append(f"- 总行数：`{total}`")
    md_lines.append(f"- 未通过行数：`{blocked_total}`（占比 `{pct((blocked_total / total) if total else 0.0)}`）")
    md_lines.append(f"- 聚类明细 CSV：`{output_csv}`")
    md_lines.append("")

    def append_table(title: str, counter: Counter[str], denominator: int) -> None:
        md_lines.append(f"## {title}")
        md_lines.append("")
        md_lines.append("| 项 | 数量 | 占比 |")
        md_lines.append("|---|---:|---:|")
        for key, count in counter.most_common(args.top_n):
            ratio = (count / denominator) if denominator else 0.0
            md_lines.append(f"| {key} | {count} | {pct(ratio)} |")
        md_lines.append("")

    append_table("决策分布（未通过）", decision_counter, blocked_total)
    append_table("分数分桶（未通过）", score_bucket_counter, blocked_total)
    append_table("错误类型（未通过）", error_counter, blocked_total)
    append_table("后置规则命中（未通过）", post_rule_counter, blocked_total)
    append_table("问题短语 Top（未通过）", issue_counter, blocked_total)

    md_lines.append("## 最低分样本（Top 10）")
    md_lines.append("")
    md_lines.append("| id | score | decision | post_rule | issue_excerpt |")
    md_lines.append("|---|---:|---|---|---|")
    for row in low_score_rows:
        issue_excerpt = (row.get("ai_issues", "") or "").replace("\n", " ").strip()
        if len(issue_excerpt) > 120:
            issue_excerpt = issue_excerpt[:117] + "..."
        md_lines.append(
            "| {id} | {score} | {decision} | {post_rule} | {issue} |".format(
                id=row.get("id", ""),
                score=row.get("ai_score", "0"),
                decision=row.get("ai_decision", ""),
                post_rule=row.get("ai_post_rule", ""),
                issue=issue_excerpt,
            )
        )
    md_lines.append("")

    output_md.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"Failure cluster report written:")
    print(f"- csv: {output_csv}")
    print(f"- md:  {output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

