#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def now_tag() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run baseline audit -> cluster -> rewrite -> second audit/recheck.")
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument(
        "--input-csv",
        default="artifacts/web_seed_v4_prefetch/knowledge_base_web.csv",
        help="Input KB candidate CSV.",
    )
    parser.add_argument(
        "--output-root",
        default="artifacts/v4_repair_round",
        help="Output root directory.",
    )
    parser.add_argument("--audit-min-score", type=int, default=72, help="Audit min score.")
    parser.add_argument("--recheck-min-score", type=int, default=82, help="Recheck min score.")
    parser.add_argument("--openai-base-url", required=True, help="OpenAI base URL.")
    parser.add_argument("--openai-api-key", required=True, help="OpenAI API key.")
    parser.add_argument("--openai-model", default="gpt-5.2-codex", help="Primary model.")
    parser.add_argument(
        "--openai-api",
        default="openai-responses",
        help="API mode: auto | chat-completions | responses | openai-responses",
    )
    parser.add_argument(
        "--openai-fallback-models",
        default="grok-3-mini,grok-4,grok-3",
        help="Fallback models.",
    )
    parser.add_argument("--openai-timeout", type=float, default=60.0, help="API timeout seconds.")
    parser.add_argument("--openai-insecure-tls", action="store_true", help="Disable TLS verify.")
    parser.add_argument("--strict-high-risk", action="store_true", help="Enable strict high-risk post rules.")
    return parser.parse_args()


def run_cmd(cmd: list[str], cwd: Path) -> dict:
    completed = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=False)
    return {
        "command": cmd,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def sanitize_command(cmd: list[str]) -> list[str]:
    sanitized: list[str] = []
    i = 0
    while i < len(cmd):
        token = cmd[i]
        sanitized.append(token)
        if token == "--openai-api-key" and i + 1 < len(cmd):
            sanitized.append("***REDACTED***")
            i += 2
            continue
        i += 1
    return sanitized


def summarize_run(step: dict) -> dict:
    return {
        "command": sanitize_command(step["command"]),
        "returncode": step["returncode"],
        "stdout_tail": step["stdout"][-3000:],
        "stderr_tail": step["stderr"][-3000:],
    }


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    python = sys.executable

    input_csv = Path(args.input_csv)
    if not input_csv.is_absolute():
        input_csv = (repo_root / input_csv).resolve()
    if not input_csv.exists():
        raise SystemExit(f"Input CSV not found: {input_csv}")

    run_dir = Path(args.output_root).resolve() / f"run_{now_tag()}"
    baseline_dir = run_dir / "baseline_audit"
    baseline_cluster_dir = run_dir / "baseline_cluster"
    rewrite_dir = run_dir / "rewrite"
    second_audit_dir = run_dir / "second_audit"
    second_cluster_dir = run_dir / "second_cluster"
    second_recheck_dir = run_dir / "second_recheck"
    run_dir.mkdir(parents=True, exist_ok=True)

    steps: dict[str, dict] = {}

    common_openai = [
        "--openai-base-url",
        args.openai_base_url,
        "--openai-api-key",
        args.openai_api_key,
        "--openai-model",
        args.openai_model,
        "--openai-api",
        args.openai_api,
        "--openai-fallback-models",
        args.openai_fallback_models,
        "--openai-timeout",
        str(args.openai_timeout),
    ]
    if args.openai_insecure_tls:
        common_openai.append("--openai-insecure-tls")

    baseline_review_csv = baseline_dir / "ai_review_audit.csv"
    baseline_pass_csv = baseline_dir / "knowledge_base_audit_pass.csv"

    cmd_baseline_audit = [
        python,
        str(repo_root / "scripts" / "ai_review_kb.py"),
        "--input-csv",
        str(input_csv),
        "--output-dir",
        str(baseline_dir),
        "--stage",
        "audit",
        "--min-score",
        str(args.audit_min_score),
        *common_openai,
    ]
    if args.strict_high_risk:
        cmd_baseline_audit.append("--strict-high-risk")
    step = run_cmd(cmd_baseline_audit, cwd=repo_root)
    steps["baseline_audit"] = summarize_run(step)
    if step["returncode"] != 0:
        raise SystemExit("Baseline audit failed.")

    cmd_baseline_cluster = [
        python,
        str(repo_root / "scripts" / "analyze_ai_review_failures.py"),
        "--input-csv",
        str(baseline_review_csv),
        "--output-csv",
        str(baseline_cluster_dir / "failure_clusters.csv"),
        "--output-md",
        str(baseline_cluster_dir / "failure_clusters.md"),
    ]
    step = run_cmd(cmd_baseline_cluster, cwd=repo_root)
    steps["baseline_cluster"] = summarize_run(step)
    if step["returncode"] != 0:
        raise SystemExit("Baseline cluster analysis failed.")

    rewritten_csv = rewrite_dir / "knowledge_base_rewritten.csv"
    rewrite_log_csv = rewrite_dir / "rewrite_log.csv"
    cmd_rewrite = [
        python,
        str(repo_root / "scripts" / "rewrite_needs_fix_rows.py"),
        "--input-csv",
        str(input_csv),
        "--review-csv",
        str(baseline_review_csv),
        "--output-csv",
        str(rewritten_csv),
        "--log-csv",
        str(rewrite_log_csv),
        *common_openai,
    ]
    step = run_cmd(cmd_rewrite, cwd=repo_root)
    steps["rewrite"] = summarize_run(step)
    if step["returncode"] != 0:
        raise SystemExit("Rewrite step failed.")

    second_review_csv = second_audit_dir / "ai_review_audit.csv"
    second_pass_csv = second_audit_dir / "knowledge_base_audit_pass.csv"
    cmd_second_audit = [
        python,
        str(repo_root / "scripts" / "ai_review_kb.py"),
        "--input-csv",
        str(rewritten_csv),
        "--output-dir",
        str(second_audit_dir),
        "--stage",
        "audit",
        "--min-score",
        str(args.audit_min_score),
        *common_openai,
    ]
    if args.strict_high_risk:
        cmd_second_audit.append("--strict-high-risk")
    step = run_cmd(cmd_second_audit, cwd=repo_root)
    steps["second_audit"] = summarize_run(step)
    if step["returncode"] != 0:
        raise SystemExit("Second audit failed.")

    cmd_second_cluster = [
        python,
        str(repo_root / "scripts" / "analyze_ai_review_failures.py"),
        "--input-csv",
        str(second_review_csv),
        "--output-csv",
        str(second_cluster_dir / "failure_clusters.csv"),
        "--output-md",
        str(second_cluster_dir / "failure_clusters.md"),
    ]
    step = run_cmd(cmd_second_cluster, cwd=repo_root)
    steps["second_cluster"] = summarize_run(step)
    if step["returncode"] != 0:
        raise SystemExit("Second cluster analysis failed.")

    cmd_second_recheck = [
        python,
        str(repo_root / "scripts" / "ai_review_kb.py"),
        "--input-csv",
        str(second_pass_csv),
        "--output-dir",
        str(second_recheck_dir),
        "--stage",
        "recheck",
        "--min-score",
        str(args.recheck_min_score),
        *common_openai,
    ]
    if args.strict_high_risk:
        cmd_second_recheck.append("--strict-high-risk")
    step = run_cmd(cmd_second_recheck, cwd=repo_root)
    steps["second_recheck"] = summarize_run(step)
    if step["returncode"] != 0:
        raise SystemExit("Second recheck failed.")

    baseline_report = load_json(baseline_dir / "ai_review_report_audit.json")
    second_audit_report = load_json(second_audit_dir / "ai_review_report_audit.json")
    second_recheck_report = load_json(second_recheck_dir / "ai_review_report_recheck.json")

    summary = {
        "generated_at": now_iso(),
        "run_dir": str(run_dir),
        "input_csv": str(input_csv),
        "baseline": baseline_report,
        "second_audit": second_audit_report,
        "second_recheck": second_recheck_report,
        "improvement": {
            "audit_pass_rate_delta": round(
                float(second_audit_report.get("pass_rate", 0.0)) - float(baseline_report.get("pass_rate", 0.0)),
                4,
            ),
            "audit_pass_rows_delta": int(second_audit_report.get("pass_rows", 0))
            - int(baseline_report.get("pass_rows", 0)),
        },
        "steps": steps,
        "artifacts": {
            "baseline_cluster_md": str(baseline_cluster_dir / "failure_clusters.md"),
            "rewrite_csv": str(rewritten_csv),
            "rewrite_log_csv": str(rewrite_log_csv),
            "second_cluster_md": str(second_cluster_dir / "failure_clusters.md"),
            "second_recheck_pass_csv": str(second_recheck_dir / "knowledge_base_recheck_pass.csv"),
        },
    }

    summary_json = run_dir / "repair_round_report.json"
    summary_md = run_dir / "repair_round_report.md"
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# v4 二轮修复报告",
        "",
        f"- 生成时间：`{summary['generated_at']}`",
        f"- 运行目录：`{run_dir}`",
        f"- 输入数据：`{input_csv}`",
        "",
        "## 审核通过率变化",
        "",
        "| 阶段 | 总条目 | 通过条目 | 通过率 | 调用错误率 | 解析错误率 |",
        "|---|---:|---:|---:|---:|---:|",
        "| baseline audit | {t1} | {p1} | {r1:.2%} | {c1:.2%} | {j1:.2%} |".format(
            t1=int(baseline_report.get("total_rows", 0)),
            p1=int(baseline_report.get("pass_rows", 0)),
            r1=float(baseline_report.get("pass_rate", 0.0)),
            c1=float(baseline_report.get("call_error_rate", 0.0)),
            j1=float(baseline_report.get("parse_error_rate", 0.0)),
        ),
        "| second audit | {t2} | {p2} | {r2:.2%} | {c2:.2%} | {j2:.2%} |".format(
            t2=int(second_audit_report.get("total_rows", 0)),
            p2=int(second_audit_report.get("pass_rows", 0)),
            r2=float(second_audit_report.get("pass_rate", 0.0)),
            c2=float(second_audit_report.get("call_error_rate", 0.0)),
            j2=float(second_audit_report.get("parse_error_rate", 0.0)),
        ),
        "| second recheck | {t3} | {p3} | {r3:.2%} | {c3:.2%} | {j3:.2%} |".format(
            t3=int(second_recheck_report.get("total_rows", 0)),
            p3=int(second_recheck_report.get("pass_rows", 0)),
            r3=float(second_recheck_report.get("pass_rate", 0.0)),
            c3=float(second_recheck_report.get("call_error_rate", 0.0)),
            j3=float(second_recheck_report.get("parse_error_rate", 0.0)),
        ),
        "",
        "## 产物路径",
        "",
        f"- baseline 聚类：`{summary['artifacts']['baseline_cluster_md']}`",
        f"- 改写后 CSV：`{summary['artifacts']['rewrite_csv']}`",
        f"- 改写日志：`{summary['artifacts']['rewrite_log_csv']}`",
        f"- second 聚类：`{summary['artifacts']['second_cluster_md']}`",
        f"- 二轮复检通过 CSV：`{summary['artifacts']['second_recheck_pass_csv']}`",
    ]
    summary_md.write_text("\n".join(lines), encoding="utf-8")

    print("Repair round completed:")
    print(f"- report json: {summary_json}")
    print(f"- report md:   {summary_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

