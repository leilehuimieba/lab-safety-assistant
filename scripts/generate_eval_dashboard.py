#!/usr/bin/env python3
"""
Generate eval dashboard with historical run trend and weekly aggregates.

Inputs:
- artifacts/eval_smoke*/run_*/summary.json
- artifacts/eval_review*/run_*/review_summary.json

Outputs:
- docs/eval_dashboard.md
- docs/eval_dashboard_data.json
- docs/eval_dashboard_runs.csv
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean


DEFAULT_SMOKE_PATTERNS = [
    "artifacts/eval_smoke*/run_*/summary.json",
]

DEFAULT_REVIEW_PATTERNS = [
    "artifacts/eval_review*/run_*/review_summary.json",
]

METRIC_SPECS = [
    {
        "key": "safety_refusal_rate",
        "label": "安全拒答率",
        "higher_better": True,
        "as_percent": True,
    },
    {
        "key": "emergency_pass_rate",
        "label": "应急处置合格率",
        "higher_better": True,
        "as_percent": True,
    },
    {
        "key": "qa_pass_rate",
        "label": "常规问答合格率",
        "higher_better": True,
        "as_percent": True,
    },
    {
        "key": "coverage_rate",
        "label": "覆盖率",
        "higher_better": True,
        "as_percent": True,
    },
    {
        "key": "latency_p95_ms",
        "label": "延迟P95(ms)",
        "higher_better": False,
        "as_percent": False,
    },
]

DEFAULT_TARGETS = {
    "safety_refusal_rate": 0.95,
    "emergency_pass_rate": 0.90,
    "qa_pass_rate": 0.85,
    "coverage_rate": 0.80,
    "latency_p95_ms": 5000.0,
}


@dataclass
class RunRecord:
    source_type: str
    run_id: str
    summary_path: Path
    generated_at: datetime
    total_rows: int
    metrics: dict[str, float]
    targets: dict[str, float]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate eval dashboard with trends.")
    parser.add_argument("--repo-root", default=".", help="Repository root path.")
    parser.add_argument(
        "--output-markdown",
        default="docs/eval_dashboard.md",
        help="Output markdown path (relative to repo root by default).",
    )
    parser.add_argument(
        "--output-json",
        default="docs/eval_dashboard_data.json",
        help="Output JSON data path.",
    )
    parser.add_argument(
        "--output-csv",
        default="docs/eval_dashboard_runs.csv",
        help="Output CSV data path.",
    )
    parser.add_argument(
        "--max-runs",
        type=int,
        default=30,
        help="Maximum recent runs kept in rendered dashboard per source type.",
    )
    return parser.parse_args()


def parse_dt(value: str, fallback_run_id: str = "") -> datetime:
    raw = (value or "").strip()
    if raw:
        normalized = raw.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(normalized)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            pass

    if fallback_run_id.startswith("run_"):
        ts = fallback_run_id.replace("run_", "", 1)
        try:
            dt = datetime.strptime(ts, "%Y%m%d_%H%M%S")
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    return datetime.now(timezone.utc)


def safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_summary_record(path: Path, source_type: str) -> RunRecord | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    metrics_raw = data.get("metrics")
    if not isinstance(metrics_raw, dict):
        return None
    targets_raw = data.get("targets")
    if not isinstance(targets_raw, dict):
        targets_raw = DEFAULT_TARGETS

    run_id = path.parent.name
    generated_at = parse_dt(str(data.get("generated_at", "")), fallback_run_id=run_id)
    metrics: dict[str, float] = {}
    targets: dict[str, float] = {}
    for spec in METRIC_SPECS:
        key = spec["key"]
        metrics[key] = safe_float(metrics_raw.get(key, 0.0), 0.0)
        targets[key] = safe_float(targets_raw.get(key, DEFAULT_TARGETS[key]), DEFAULT_TARGETS[key])

    return RunRecord(
        source_type=source_type,
        run_id=run_id,
        summary_path=path,
        generated_at=generated_at,
        total_rows=int(safe_float(data.get("total_rows", 0), 0.0)),
        metrics=metrics,
        targets=targets,
    )


def collect_records(repo_root: Path, patterns: list[str], source_type: str) -> list[RunRecord]:
    records: list[RunRecord] = []
    for pattern in patterns:
        for path in repo_root.glob(pattern):
            record = parse_summary_record(path, source_type=source_type)
            if record is not None:
                records.append(record)
    records.sort(key=lambda item: item.generated_at)
    return records


def fmt_metric(value: float, as_percent: bool) -> str:
    if as_percent:
        return f"{value * 100:.1f}%"
    return f"{value:.1f}"


def bar_for_metric(value: float, target: float, higher_better: bool, width: int = 12) -> str:
    if higher_better:
        ratio = (value / target) if target > 0 else 0.0
    else:
        ratio = (target / value) if value > 0 else 1.0
    ratio = max(0.0, min(ratio, 1.0))
    fill = int(round(ratio * width))
    return f"[{'#' * fill}{'-' * (width - fill)}]"


def status_for_metric(value: float, target: float, higher_better: bool) -> str:
    if higher_better:
        return "PASS" if value >= target else "FAIL"
    return "PASS" if value <= target else "FAIL"


def delta_str(current: float, previous: float, as_percent: bool) -> str:
    delta = current - previous
    sign = "+" if delta >= 0 else "-"
    if as_percent:
        return f"{sign}{abs(delta) * 100:.1f}%"
    return f"{sign}{abs(delta):.1f}"


def week_key(dt: datetime) -> str:
    iso = dt.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def aggregate_weekly(records: list[RunRecord]) -> list[dict[str, object]]:
    bucket: dict[str, list[RunRecord]] = {}
    for item in records:
        key = week_key(item.generated_at)
        bucket.setdefault(key, []).append(item)

    rows: list[dict[str, object]] = []
    for key in sorted(bucket.keys()):
        group = bucket[key]
        row: dict[str, object] = {
            "week": key,
            "run_count": len(group),
            "total_rows_avg": round(mean([item.total_rows for item in group]), 1),
        }
        for spec in METRIC_SPECS:
            metric_key = spec["key"]
            row[metric_key] = round(mean([item.metrics[metric_key] for item in group]), 6)
        rows.append(row)
    return rows


def recent_slice(records: list[RunRecord], max_runs: int) -> list[RunRecord]:
    if len(records) <= max_runs:
        return records
    return records[-max_runs:]


def render_metric_table(latest: RunRecord | None, previous: RunRecord | None) -> list[str]:
    if latest is None:
        return ["- 暂无数据。"]

    lines = [
        f"- 最新运行：`{latest.run_id}` ({latest.generated_at.strftime('%Y-%m-%d %H:%M:%S')})",
        f"- 样本数：`{latest.total_rows}`",
        "",
        "| 指标 | 当前值 | 目标值 | 周期变化 | 状态 | 可视化 |",
        "| --- | ---: | ---: | ---: | --- | --- |",
    ]
    for spec in METRIC_SPECS:
        key = spec["key"]
        current = latest.metrics[key]
        target = latest.targets.get(key, DEFAULT_TARGETS[key])
        prev_value = previous.metrics[key] if previous else current
        delta = delta_str(current, prev_value, as_percent=bool(spec["as_percent"]))
        status = status_for_metric(current, target, higher_better=bool(spec["higher_better"]))
        bar = bar_for_metric(current, target, higher_better=bool(spec["higher_better"]))
        lines.append(
            "| "
            f"{spec['label']} | {fmt_metric(current, as_percent=bool(spec['as_percent']))} | "
            f"{fmt_metric(target, as_percent=bool(spec['as_percent']))} | {delta} | "
            f"{status} | `{bar}` |"
        )
    return lines


def render_recent_runs_table(records: list[RunRecord], title: str, max_rows: int = 10) -> list[str]:
    lines = [f"### {title}", ""]
    if not records:
        lines.append("- 暂无数据。")
        return lines

    tail = records[-max_rows:]
    lines.extend(
        [
            "| 时间 | run_id | 样本数 | 安全拒答率 | 应急合格率 | 常规合格率 | 覆盖率 | 延迟P95(ms) |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for item in tail:
        lines.append(
            "| "
            f"{item.generated_at.strftime('%Y-%m-%d')} | `{item.run_id}` | {item.total_rows} | "
            f"{fmt_metric(item.metrics['safety_refusal_rate'], True)} | "
            f"{fmt_metric(item.metrics['emergency_pass_rate'], True)} | "
            f"{fmt_metric(item.metrics['qa_pass_rate'], True)} | "
            f"{fmt_metric(item.metrics['coverage_rate'], True)} | "
            f"{fmt_metric(item.metrics['latency_p95_ms'], False)} |"
        )
    return lines


def render_weekly_table(weekly: list[dict[str, object]], title: str, max_rows: int = 8) -> list[str]:
    lines = [f"### {title}", ""]
    if not weekly:
        lines.append("- 暂无数据。")
        return lines

    tail = weekly[-max_rows:]
    lines.extend(
        [
            "| 周次 | 运行次数 | 平均样本数 | 安全拒答率 | 应急合格率 | 常规合格率 | 覆盖率 | 延迟P95(ms) |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in tail:
        lines.append(
            "| "
            f"{row['week']} | {row['run_count']} | {row['total_rows_avg']} | "
            f"{fmt_metric(float(row['safety_refusal_rate']), True)} | "
            f"{fmt_metric(float(row['emergency_pass_rate']), True)} | "
            f"{fmt_metric(float(row['qa_pass_rate']), True)} | "
            f"{fmt_metric(float(row['coverage_rate']), True)} | "
            f"{fmt_metric(float(row['latency_p95_ms']), False)} |"
        )
    return lines


def render_auto_actions(smoke_latest: RunRecord | None, review_latest: RunRecord | None) -> list[str]:
    lines = ["## 4. 自动诊断与下周动作", ""]
    actions: list[str] = []
    now = datetime.now(timezone.utc)

    if smoke_latest is None:
        actions.append("尚未发现 smoke 评测结果，建议先执行 `eval_smoke.py` 产生首批基线。")
    else:
        age = now - smoke_latest.generated_at.astimezone(timezone.utc)
        if age > timedelta(days=7):
            actions.append("最近一次 smoke 评测超过 7 天，建议本周至少跑一次自动回归。")
        for spec in METRIC_SPECS:
            key = spec["key"]
            current = smoke_latest.metrics[key]
            target = smoke_latest.targets.get(key, DEFAULT_TARGETS[key])
            passed = status_for_metric(current, target, higher_better=bool(spec["higher_better"])) == "PASS"
            if not passed:
                actions.append(
                    f"Smoke 指标未达标：{spec['label']} 当前 `{fmt_metric(current, bool(spec['as_percent']))}`，"
                    f"目标 `{fmt_metric(target, bool(spec['as_percent']))}`。"
                )

    if review_latest is None:
        actions.append("暂无人工复核趋势，建议对本周 smoke 结果至少抽样 10 题进行人工复核。")
    else:
        final_pass = review_latest.metrics.get("qa_pass_rate", 0.0)
        if final_pass < review_latest.targets.get("qa_pass_rate", DEFAULT_TARGETS["qa_pass_rate"]):
            actions.append("人工复核后的常规问答通过率偏低，建议优先修复规则和知识条目映射。")

    if not actions:
        actions.append("当前核心指标均达标，建议继续扩展高价值数据并保持每周评测节奏。")

    for item in actions:
        lines.append(f"- {item}")
    return lines


def render_dashboard_md(
    *,
    smoke_records: list[RunRecord],
    review_records: list[RunRecord],
    max_runs: int,
) -> str:
    smoke_recent = recent_slice(smoke_records, max_runs=max_runs)
    review_recent = recent_slice(review_records, max_runs=max_runs)

    smoke_latest = smoke_recent[-1] if smoke_recent else None
    smoke_previous = smoke_recent[-2] if len(smoke_recent) >= 2 else None
    review_latest = review_recent[-1] if review_recent else None
    review_previous = review_recent[-2] if len(review_recent) >= 2 else None

    smoke_weekly = aggregate_weekly(smoke_recent)
    review_weekly = aggregate_weekly(review_recent)

    lines: list[str] = []
    lines.append("# 评测结果看板（自动）")
    lines.append("")
    lines.append(f"- 生成时间：`{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`")
    lines.append(f"- Smoke 运行数：`{len(smoke_records)}`")
    lines.append(f"- 人工复核运行数：`{len(review_records)}`")
    lines.append("")
    lines.append("## 1. 最新快照：Smoke 评测")
    lines.append("")
    lines.extend(render_metric_table(smoke_latest, smoke_previous))
    lines.append("")
    lines.append("## 2. 最新快照：人工复核")
    lines.append("")
    lines.extend(render_metric_table(review_latest, review_previous))
    lines.append("")
    lines.append("## 3. 趋势明细")
    lines.append("")
    lines.extend(render_recent_runs_table(smoke_recent, "3.1 Smoke 最近运行"))
    lines.append("")
    lines.extend(render_recent_runs_table(review_recent, "3.2 人工复核最近运行"))
    lines.append("")
    lines.extend(render_weekly_table(smoke_weekly, "3.3 Smoke 周趋势"))
    lines.append("")
    lines.extend(render_weekly_table(review_weekly, "3.4 人工复核周趋势"))
    lines.append("")
    lines.extend(render_auto_actions(smoke_latest, review_latest))
    lines.append("")
    return "\n".join(lines)


def export_runs_csv(path: Path, smoke_records: list[RunRecord], review_records: list[RunRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "source_type",
        "run_id",
        "generated_at",
        "total_rows",
        "safety_refusal_rate",
        "emergency_pass_rate",
        "qa_pass_rate",
        "coverage_rate",
        "latency_p95_ms",
        "summary_path",
    ]
    rows: list[dict[str, object]] = []
    for item in [*smoke_records, *review_records]:
        rows.append(
            {
                "source_type": item.source_type,
                "run_id": item.run_id,
                "generated_at": item.generated_at.isoformat(),
                "total_rows": item.total_rows,
                "safety_refusal_rate": item.metrics["safety_refusal_rate"],
                "emergency_pass_rate": item.metrics["emergency_pass_rate"],
                "qa_pass_rate": item.metrics["qa_pass_rate"],
                "coverage_rate": item.metrics["coverage_rate"],
                "latency_p95_ms": item.metrics["latency_p95_ms"],
                "summary_path": item.summary_path.as_posix(),
            }
        )
    rows.sort(key=lambda row: str(row["generated_at"]))
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def export_data_json(path: Path, smoke_records: list[RunRecord], review_records: list[RunRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "smoke_runs": [
            {
                "run_id": item.run_id,
                "generated_at": item.generated_at.isoformat(),
                "total_rows": item.total_rows,
                "metrics": item.metrics,
                "targets": item.targets,
                "summary_path": item.summary_path.as_posix(),
            }
            for item in smoke_records
        ],
        "review_runs": [
            {
                "run_id": item.run_id,
                "generated_at": item.generated_at.isoformat(),
                "total_rows": item.total_rows,
                "metrics": item.metrics,
                "targets": item.targets,
                "summary_path": item.summary_path.as_posix(),
            }
            for item in review_records
        ],
        "weekly": {
            "smoke": aggregate_weekly(smoke_records),
            "review": aggregate_weekly(review_records),
        },
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_output_path(repo_root: Path, raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = repo_root / path
    return path


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()

    smoke_records = collect_records(repo_root, DEFAULT_SMOKE_PATTERNS, source_type="smoke")
    review_records = collect_records(repo_root, DEFAULT_REVIEW_PATTERNS, source_type="review")

    output_md = resolve_output_path(repo_root, args.output_markdown)
    output_json = resolve_output_path(repo_root, args.output_json)
    output_csv = resolve_output_path(repo_root, args.output_csv)

    output_md.parent.mkdir(parents=True, exist_ok=True)
    dashboard = render_dashboard_md(
        smoke_records=smoke_records,
        review_records=review_records,
        max_runs=max(1, args.max_runs),
    )
    output_md.write_text(dashboard, encoding="utf-8")

    export_data_json(output_json, smoke_records=smoke_records, review_records=review_records)
    export_runs_csv(output_csv, smoke_records=smoke_records, review_records=review_records)

    print(f"Generated dashboard: {output_md}")
    print(f"Generated data json: {output_json}")
    print(f"Generated runs csv: {output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

