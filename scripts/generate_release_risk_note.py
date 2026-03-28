#!/usr/bin/env python3
"""
Generate an auto release risk note from eval dashboard outputs.
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import validate_eval_dashboard_gate as veg


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate auto release risk note from eval dashboard + gate."
    )
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument(
        "--dashboard-data",
        default="docs/eval/eval_dashboard_data.json",
        help="Path to eval dashboard data json.",
    )
    parser.add_argument(
        "--override-config",
        default="docs/eval/eval_dashboard_gate_override.json",
        help="Optional gate override config path.",
    )
    parser.add_argument(
        "--output-md",
        default="docs/eval/release_risk_note_auto.md",
        help="Output markdown path.",
    )
    parser.add_argument(
        "--output-json",
        default="docs/eval/release_risk_note_auto.json",
        help="Output json path.",
    )
    parser.add_argument(
        "--weeks",
        type=int,
        default=2,
        help="Consecutive week window for gate judgment.",
    )
    parser.add_argument(
        "--metrics",
        default=",".join(veg.DEFAULT_METRICS),
        help="Quality metrics keys.",
    )
    parser.add_argument(
        "--route-metrics",
        default=",".join(veg.DEFAULT_ROUTE_METRICS),
        help="Route metrics keys.",
    )
    parser.add_argument(
        "--route-success-threshold-for-quality",
        type=float,
        default=0.70,
        help="Only enforce quality metrics on route-healthy weeks.",
    )
    return parser.parse_args()


def resolve_path(repo_root: Path, raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = repo_root / path
    return path.resolve()


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def fvalue(mapping: dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return float(mapping.get(key, default) or default)
    except (TypeError, ValueError):
        return default


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    dashboard_path = resolve_path(repo_root, args.dashboard_data)
    override_path = resolve_path(repo_root, args.override_config)
    output_md = resolve_path(repo_root, args.output_md)
    output_json = resolve_path(repo_root, args.output_json)

    if not dashboard_path.exists():
        raise SystemExit(f"dashboard data not found: {dashboard_path}")

    data = json.loads(dashboard_path.read_text(encoding="utf-8"))
    smoke_runs = data.get("smoke_runs", []) if isinstance(data, dict) else []
    latest_smoke = smoke_runs[-1] if smoke_runs else {}
    if not isinstance(latest_smoke, dict):
        latest_smoke = {}

    metrics = [m.strip() for m in args.metrics.split(",") if m.strip()]
    route_metrics = [m.strip() for m in args.route_metrics.split(",") if m.strip()]

    weekly_rows, targets = veg.load_dashboard_weekly(dashboard_path)
    route_violations = veg.evaluate_consecutive_week_violations(
        weekly_rows,
        targets=targets,
        metrics=route_metrics,
        weeks=max(2, args.weeks),
    )
    quality_rows = [
        row
        for row in weekly_rows
        if row.metrics.get("route_success_rate", 0.0)
        >= args.route_success_threshold_for_quality
    ]
    quality_violations = veg.evaluate_consecutive_week_violations(
        quality_rows,
        targets=targets,
        metrics=metrics,
        weeks=max(2, args.weeks),
    )
    violations = [*route_violations, *quality_violations]

    override = veg.load_override_config(override_path)
    override_active = veg.is_override_active(override, today=date.today())
    override_warn_only = bool(
        override_active and override is not None and override.mode == "warn_only"
    )

    if violations and not override_warn_only:
        gate_decision = "BLOCK"
    elif violations and override_warn_only:
        gate_decision = "WARN_ONLY"
    else:
        gate_decision = "PASS"

    latest_metrics = (
        latest_smoke.get("metrics", {}) if isinstance(latest_smoke.get("metrics", {}), dict) else {}
    )
    latest_route_stats = (
        latest_smoke.get("route_stats", {})
        if isinstance(latest_smoke.get("route_stats", {}), dict)
        else {}
    )

    payload = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "gate_decision": gate_decision,
        "violations": violations,
        "override_active": override_active,
        "override_mode": (override.mode if override else ""),
        "override_reason": (override.reason if override else ""),
        "override_ticket": (override.ticket if override else ""),
        "override_approver": (override.approver if override else ""),
        "latest_smoke_run_id": str(latest_smoke.get("run_id", "")),
        "latest_smoke_generated_at": str(latest_smoke.get("generated_at", "")),
        "latest_metrics": latest_metrics,
        "latest_route_stats": latest_route_stats,
        "targets": targets,
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines: list[str] = []
    lines.append("# 发布风险说明（自动）")
    lines.append("")
    lines.append(f"- 生成时间：`{payload['generated_at']}`")
    lines.append(f"- 门禁判定：`{gate_decision}`")
    lines.append(f"- 最新 Smoke 运行：`{payload['latest_smoke_run_id']}`")
    lines.append("")
    lines.append("## 1) 最新链路与质量快照")
    lines.append("")
    lines.append("| 指标 | 当前值 | 目标值 |")
    lines.append("|---|---:|---:|")
    lines.append(
        f"| 链路可用率 | {pct(fvalue(latest_route_stats, 'route_success_rate'))} | "
        f"{pct(fvalue(targets, 'route_success_rate', 0.7))} |"
    )
    lines.append(
        f"| 超时率 | {pct(fvalue(latest_route_stats, 'route_timeout_rate'))} | "
        f"{pct(fvalue(targets, 'route_timeout_rate', 0.3))} |"
    )
    lines.append(
        f"| 安全拒答率 | {pct(fvalue(latest_metrics, 'safety_refusal_rate'))} | "
        f"{pct(fvalue(targets, 'safety_refusal_rate', 0.95))} |"
    )
    lines.append(
        f"| 应急合格率 | {pct(fvalue(latest_metrics, 'emergency_pass_rate'))} | "
        f"{pct(fvalue(targets, 'emergency_pass_rate', 0.90))} |"
    )
    lines.append(
        f"| 常规问答合格率 | {pct(fvalue(latest_metrics, 'qa_pass_rate'))} | "
        f"{pct(fvalue(targets, 'qa_pass_rate', 0.85))} |"
    )
    lines.append(
        f"| 模糊问答合格率 | {pct(fvalue(latest_metrics, 'fuzzy_pass_rate'))} | "
        f"{pct(fvalue(targets, 'fuzzy_pass_rate', 0.80))} |"
    )
    lines.append("")
    lines.append("## 2) 门禁违规项")
    lines.append("")
    if violations:
        for item in violations:
            lines.append(f"- {item}")
    else:
        lines.append("- 无连续周违规项。")
    lines.append("")
    lines.append("## 3) 临时豁免信息")
    lines.append("")
    if override_active and override is not None:
        lines.append(f"- 模式：`{override.mode}`")
        if override.starts_on:
            lines.append(f"- 生效开始：`{override.starts_on.isoformat()}`")
        if override.ends_on:
            lines.append(f"- 生效结束：`{override.ends_on.isoformat()}`")
        if override.reason:
            lines.append(f"- 原因：{override.reason}")
        if override.ticket:
            lines.append(f"- 关联单号：{override.ticket}")
        if override.approver:
            lines.append(f"- 审批人：{override.approver}")
    else:
        lines.append("- 当前未启用豁免窗口。")
    lines.append("")
    lines.append("## 4) 发布建议")
    lines.append("")
    if gate_decision == "PASS":
        lines.append("- 建议：可发布。")
    elif gate_decision == "WARN_ONLY":
        lines.append("- 建议：可临时发布（告警放行），需在下个周期关闭链路风险。")
    else:
        lines.append("- 建议：禁止发布，优先修复链路健康问题。")
    lines.append("")
    lines.append(f"- JSON 明细：`{output_json}`")
    lines.append("")

    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text("\n".join(lines), encoding="utf-8")

    print("Generated risk note:")
    print(f"- {output_md}")
    print(f"- {output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
