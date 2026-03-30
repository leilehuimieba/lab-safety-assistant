#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate go-live failure digest from latest artifacts.")
    parser.add_argument("--repo-root", default=".", help="Repository root path.")
    parser.add_argument(
        "--bundle-json",
        default="docs/ops/go_live_bundle_latest.json",
        help="Path to go-live bundle summary JSON.",
    )
    parser.add_argument(
        "--go-live-json",
        default="docs/ops/go_live_readiness.json",
        help="Path to go-live preflight JSON.",
    )
    parser.add_argument(
        "--stability-json",
        default="docs/eval/release_stability_check.json",
        help="Path to release stability summary JSON.",
    )
    parser.add_argument(
        "--output-json",
        default="docs/ops/go_live_failure_digest_latest.json",
        help="Output digest JSON path.",
    )
    parser.add_argument(
        "--output-md",
        default="docs/ops/go_live_failure_digest_latest.md",
        help="Output digest markdown path.",
    )
    return parser.parse_args()


def resolve(repo_root: Path, rel_or_abs: str) -> Path:
    p = Path(rel_or_abs)
    if p.is_absolute():
        return p
    return (repo_root / p).resolve()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def safe_tail(text: str, limit: int = 800) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[-limit:]


def find_latest_oneclick_report(repo_root: Path) -> Path | None:
    candidates = list((repo_root / "artifacts" / "release_stability_check").glob("run_*/round_*/run_*/eval_release_oneclick_report.json"))
    if not candidates:
        candidates = list((repo_root / "artifacts" / "eval_release_oneclick").glob("run_*/eval_release_oneclick_report.json"))
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: str(p))[-1]


def find_latest_health_report(repo_root: Path) -> Path | None:
    candidates = list((repo_root / "artifacts" / "live_health").glob("run_*/health_check_report.json"))
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: str(p))[-1]


def build_digest(repo_root: Path, bundle: dict[str, Any], go_live: dict[str, Any], stability: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []
    actions: list[str] = []

    bundle_overall = str(bundle.get("overall", "")).upper()
    go_live_overall = str(go_live.get("overall", "")).upper()
    stability_overall = str(stability.get("overall", "")).upper()

    steps = bundle.get("steps") if isinstance(bundle.get("steps"), dict) else {}
    failed_steps = {k: v for k, v in steps.items() if isinstance(v, dict) and not bool(v.get("ok", False))}

    for name, info in failed_steps.items():
        exit_code = info.get("exit_code", "NA")
        extra = info.get("overall")
        if extra:
            blockers.append(f"{name}: exit={exit_code}, overall={extra}")
        else:
            blockers.append(f"{name}: exit={exit_code}")

    checks = go_live.get("checks") if isinstance(go_live.get("checks"), list) else []
    for item in checks:
        if not isinstance(item, dict):
            continue
        ok = bool(item.get("ok"))
        level = str(item.get("level", "")).lower()
        key = str(item.get("key", "unknown"))
        detail = str(item.get("detail", ""))
        if ok:
            continue
        if level == "blocker":
            blockers.append(f"{key}: {detail}")
        else:
            warnings.append(f"{key}: {detail}")

    oneclick_path = find_latest_oneclick_report(repo_root)
    oneclick_payload = load_json(oneclick_path) if oneclick_path else {}
    oneclick_status = str(oneclick_payload.get("status", ""))
    if oneclick_status and oneclick_status != "success":
        blockers.append(f"release_oneclick status={oneclick_status}")

    oneclick_steps = oneclick_payload.get("steps") if isinstance(oneclick_payload.get("steps"), dict) else {}
    failover_eval = oneclick_steps.get("failover_eval") if isinstance(oneclick_steps.get("failover_eval"), dict) else {}
    stderr_tail = safe_tail(str(failover_eval.get("stderr_tail", "")))
    stdout_tail = safe_tail(str(failover_eval.get("stdout_tail", "")))

    health_path = find_latest_health_report(repo_root)
    health_payload = load_json(health_path) if health_path else {}
    health_pass = health_payload.get("pass_effective", health_payload.get("pass"))

    if bundle_overall != "PASS":
        actions.append("先处理 bundle 中失败步骤，再重跑 deploy/run_server_go_live_bundle.sh。")
    if go_live_overall == "BLOCK":
        actions.append("按 go_live_readiness 的 blocker 项逐条修复。")
    if stability_overall != "PASS":
        actions.append("重跑稳定性验收并检查 release_stability_check.md。")
    if oneclick_status and oneclick_status != "success":
        actions.append("检查 eval_release_oneclick_report.json 中 failover_eval 的 stderr_tail。")
    if health_pass is False:
        actions.append("先修复 live health 体检失败项，尤其是 embedding 和 chat preflight。")
    if not actions:
        actions.append("当前无阻塞项，可继续执行发布流程。")

    return {
        "generated_at": now_iso(),
        "overall": "BLOCK" if blockers else "PASS",
        "summary": {
            "bundle_overall": bundle_overall or "UNKNOWN",
            "go_live_overall": go_live_overall or "UNKNOWN",
            "stability_overall": stability_overall or "UNKNOWN",
            "blocker_count": len(blockers),
            "warning_count": len(warnings),
        },
        "blockers": blockers,
        "warnings": warnings,
        "signals": {
            "latest_oneclick_report": str(oneclick_path) if oneclick_path else "",
            "latest_oneclick_status": oneclick_status,
            "latest_oneclick_stdout_tail": stdout_tail,
            "latest_oneclick_stderr_tail": stderr_tail,
            "latest_health_report": str(health_path) if health_path else "",
            "latest_health_pass_effective": health_pass,
        },
        "next_actions": actions,
    }


def to_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Go-Live Failure Digest")
    lines.append("")
    lines.append(f"- Generated: `{payload.get('generated_at', '')}`")
    lines.append(f"- Overall: `{payload.get('overall', '')}`")
    summary = payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
    lines.append(
        "- Snapshot: "
        f"bundle=`{summary.get('bundle_overall', 'UNKNOWN')}` "
        f"go_live=`{summary.get('go_live_overall', 'UNKNOWN')}` "
        f"stability=`{summary.get('stability_overall', 'UNKNOWN')}`"
    )
    lines.append("")

    lines.append("## Blockers")
    blockers = payload.get("blockers", [])
    if isinstance(blockers, list) and blockers:
        for item in blockers:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    lines.append("")

    lines.append("## Warnings")
    warnings = payload.get("warnings", [])
    if isinstance(warnings, list) and warnings:
        for item in warnings:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    lines.append("")

    signals = payload.get("signals", {}) if isinstance(payload.get("signals"), dict) else {}
    lines.append("## Key Signals")
    lines.append(f"- oneclick report: `{signals.get('latest_oneclick_report', '')}`")
    lines.append(f"- oneclick status: `{signals.get('latest_oneclick_status', '')}`")
    if signals.get("latest_oneclick_stderr_tail"):
        lines.append(f"- oneclick stderr tail: `{signals.get('latest_oneclick_stderr_tail')}`")
    lines.append(f"- health report: `{signals.get('latest_health_report', '')}`")
    lines.append(f"- health pass effective: `{signals.get('latest_health_pass_effective', '')}`")
    lines.append("")

    lines.append("## Next Actions")
    actions = payload.get("next_actions", [])
    if isinstance(actions, list) and actions:
        for i, action in enumerate(actions, start=1):
            lines.append(f"{i}. {action}")
    else:
        lines.append("1. 无")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()

    bundle = load_json(resolve(repo_root, args.bundle_json))
    go_live = load_json(resolve(repo_root, args.go_live_json))
    stability = load_json(resolve(repo_root, args.stability_json))

    payload = build_digest(repo_root, bundle, go_live, stability)

    output_json = resolve(repo_root, args.output_json)
    output_md = resolve(repo_root, args.output_md)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md.write_text(to_markdown(payload), encoding="utf-8")

    print(f"go-live failure digest overall: {payload.get('overall')}")
    print(f"- output json: {output_json}")
    print(f"- output md: {output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
