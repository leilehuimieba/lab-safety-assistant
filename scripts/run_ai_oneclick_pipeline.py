#!/usr/bin/env python3
"""
One-click AI pipeline:
1) AI collect data (document + web ingestion via unified pipeline)
2) AI audit
3) AI recheck
4) AI-approved merge into KB
5) quality gate
6) optional eval regression
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


KB_FIELDNAMES = [
    "id",
    "title",
    "category",
    "subcategory",
    "lab_type",
    "risk_level",
    "hazard_types",
    "scenario",
    "question",
    "answer",
    "steps",
    "ppe",
    "forbidden",
    "disposal",
    "first_aid",
    "emergency",
    "legal_notes",
    "references",
    "source_type",
    "source_title",
    "source_org",
    "source_version",
    "source_date",
    "source_url",
    "last_updated",
    "reviewer",
    "status",
    "tags",
    "language",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def now_tag() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one-click AI full pipeline.")
    parser.add_argument("--repo-root", default=".", help="Repository root path.")
    parser.add_argument(
        "--output-root",
        default="artifacts/ai_oneclick",
        help="Root directory for one-click run artifacts.",
    )
    parser.add_argument(
        "--input-csv",
        default="",
        help="Optional input CSV. If set, skip collect step and audit this CSV directly.",
    )
    parser.add_argument(
        "--document-input-root",
        default="..\\data",
        help="Document input root for unified pipeline.",
    )
    parser.add_argument(
        "--document-manifest",
        default="data_sources\\document_manifest.csv",
        help="Document manifest for unified pipeline.",
    )
    parser.add_argument(
        "--document-pdf-special-rules",
        default="data_sources\\pdf_special_rules.csv",
        help="PDF special rules CSV path.",
    )
    parser.add_argument(
        "--pdf-ocr-mode",
        choices=["auto", "off", "always"],
        default="auto",
        help="PDF OCR mode for collect step.",
    )
    parser.add_argument(
        "--skip-web",
        action="store_true",
        help="Skip web collect step inside unified pipeline.",
    )
    parser.add_argument(
        "--web-manifest",
        default="data_sources\\web_seed_urls.csv",
        help="Web seed manifest for unified pipeline.",
    )
    parser.add_argument(
        "--web-fetcher-mode",
        choices=["auto", "legacy", "skill"],
        default="auto",
        help="Fetcher mode for web ingestion.",
    )
    parser.add_argument(
        "--web-skill-script",
        default="",
        help="Optional path to fetch_web_content.py.",
    )
    parser.add_argument(
        "--web-skill-providers",
        default="jina,scrapling,direct",
        help="Provider chain for skill mode.",
    )
    parser.add_argument(
        "--document-max-chars",
        type=int,
        default=1800,
        help="Max chars per document chunk.",
    )
    parser.add_argument(
        "--document-overlap",
        type=int,
        default=100,
        help="Document overlap chars.",
    )
    parser.add_argument(
        "--web-max-chars",
        type=int,
        default=1400,
        help="Max chars per web chunk.",
    )
    parser.add_argument(
        "--web-overlap",
        type=int,
        default=100,
        help="Web overlap chars.",
    )
    parser.add_argument(
        "--audit-min-score",
        type=int,
        default=72,
        help="Minimum score for audit pass.",
    )
    parser.add_argument(
        "--recheck-min-score",
        type=int,
        default=82,
        help="Minimum score for recheck pass.",
    )
    parser.add_argument(
        "--review-limit",
        type=int,
        default=0,
        help="Optional review row limit for quick runs (0 = all).",
    )
    parser.add_argument(
        "--strict-high-risk",
        action="store_true",
        help="Enforce strict high-risk checks during AI review/recheck.",
    )
    parser.add_argument(
        "--openai-base-url",
        default=os.environ.get("OPENAI_BASE_URL", "http://ai.little100.cn:3000/v1"),
        help="OpenAI-compatible base URL.",
    )
    parser.add_argument(
        "--openai-api-key",
        default=os.environ.get("OPENAI_API_KEY", ""),
        help="OpenAI-compatible API key.",
    )
    parser.add_argument(
        "--openai-model",
        default=os.environ.get("OPENAI_MODEL", "gpt-5.2-codex"),
        help="Primary model for AI review.",
    )
    parser.add_argument(
        "--openai-fallback-models",
        default=os.environ.get("OPENAI_FALLBACK_MODELS", "grok-3-mini,grok-4,grok-3"),
        help="Fallback models for AI review.",
    )
    parser.add_argument(
        "--openai-timeout",
        type=float,
        default=float(os.environ.get("OPENAI_TIMEOUT", "60")),
        help="Timeout seconds for AI review calls.",
    )
    parser.add_argument(
        "--merge-into",
        default="knowledge_base_curated.csv",
        help="Target KB CSV for appending AI-approved rows.",
    )
    parser.add_argument(
        "--skip-merge",
        action="store_true",
        help="Skip merge step.",
    )
    parser.add_argument(
        "--skip-quality-gate",
        action="store_true",
        help="Skip quality gate step.",
    )
    parser.add_argument(
        "--skip-eval-regression",
        action="store_true",
        help="Skip eval regression step.",
    )
    parser.add_argument(
        "--allow-skip-live-eval",
        action="store_true",
        help="Allow skipping live eval when Dify env vars are missing.",
    )
    parser.add_argument(
        "--eval-limit",
        type=int,
        default=0,
        help="Optional eval limit forwarded to run_eval_regression_pipeline.",
    )
    return parser.parse_args()


def run_cmd(cmd: list[str], cwd: Path) -> dict:
    completed = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "command": cmd,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def summarize_run(step: dict) -> dict:
    return {
        "command": step["command"],
        "returncode": step["returncode"],
        "stdout_tail": step["stdout"][-3000:],
        "stderr_tail": step["stderr"][-3000:],
    }


def count_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return sum(1 for _ in csv.DictReader(f))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [{field: (row.get(field) or "") for field in KB_FIELDNAMES} for row in reader]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=KB_FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in KB_FIELDNAMES})


def merge_unique(target: Path, incoming: Path) -> dict[str, int]:
    base_rows = read_csv_rows(target)
    incoming_rows = read_csv_rows(incoming)

    seen_ids = {row.get("id", "").strip() for row in base_rows if row.get("id")}
    appended = 0
    skipped = 0
    for row in incoming_rows:
        row_id = (row.get("id") or "").strip()
        if not row_id or row_id in seen_ids:
            skipped += 1
            continue
        base_rows.append({field: row.get(field, "") for field in KB_FIELDNAMES})
        seen_ids.add(row_id)
        appended += 1

    write_csv(target, base_rows)
    return {"incoming_rows": len(incoming_rows), "appended_rows": appended, "skipped_rows": skipped}


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

    run_dir = Path(args.output_root).resolve() / f"run_{now_tag()}"
    run_dir.mkdir(parents=True, exist_ok=True)

    unified_dir = run_dir / "unified"
    audit_dir = run_dir / "audit_stage1"
    recheck_dir = run_dir / "recheck_stage2"
    report_json = run_dir / "ai_oneclick_report.json"
    report_md = run_dir / "ai_oneclick_report.md"

    pipeline_steps: dict[str, dict] = {}

    candidate_csv: Path
    if args.input_csv:
        candidate_csv = Path(args.input_csv).resolve()
        if not candidate_csv.exists():
            raise SystemExit(f"Input CSV not found: {candidate_csv}")
    else:
        unified_cmd = [
            python,
            str(repo_root / "scripts" / "unified_kb_pipeline.py"),
            "--output-dir",
            str(unified_dir),
            "--document-input-root",
            args.document_input_root,
            "--document-manifest",
            args.document_manifest,
            "--document-only-manifest",
            "--document-pdf-special-rules",
            args.document_pdf_special_rules,
            "--pdf-ocr-mode",
            args.pdf_ocr_mode,
            "--document-max-chars",
            str(args.document_max_chars),
            "--document-overlap",
            str(args.document_overlap),
            "--web-manifest",
            args.web_manifest,
            "--web-max-chars",
            str(args.web_max_chars),
            "--web-overlap",
            str(args.web_overlap),
            "--web-fetcher-mode",
            args.web_fetcher_mode,
            "--web-skill-providers",
            args.web_skill_providers,
        ]
        if args.web_skill_script:
            unified_cmd.extend(["--web-skill-script", args.web_skill_script])
        if args.skip_web:
            unified_cmd.append("--skip-web")

        collect_run = run_cmd(unified_cmd, cwd=repo_root)
        pipeline_steps["collect"] = summarize_run(collect_run)
        if collect_run["returncode"] != 0:
            report = {
                "generated_at": now_iso(),
                "status": "failed",
                "failed_step": "collect",
                "run_dir": str(run_dir),
                "steps": pipeline_steps,
            }
            report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            raise SystemExit("Collect step failed. See ai_oneclick_report.json for details.")
        candidate_csv = unified_dir / "knowledge_base_unified.csv"
        if not candidate_csv.exists():
            raise SystemExit(f"Unified output missing: {candidate_csv}")

    audit_cmd = [
        python,
        str(repo_root / "scripts" / "ai_review_kb.py"),
        "--input-csv",
        str(candidate_csv),
        "--output-dir",
        str(audit_dir),
        "--stage",
        "audit",
        "--min-score",
        str(args.audit_min_score),
        "--openai-base-url",
        args.openai_base_url,
        "--openai-api-key",
        args.openai_api_key,
        "--openai-model",
        args.openai_model,
        "--openai-fallback-models",
        args.openai_fallback_models,
        "--openai-timeout",
        str(args.openai_timeout),
    ]
    if args.review_limit > 0:
        audit_cmd.extend(["--limit", str(args.review_limit)])
    if args.strict_high_risk:
        audit_cmd.append("--strict-high-risk")

    audit_run = run_cmd(audit_cmd, cwd=repo_root)
    pipeline_steps["audit"] = summarize_run(audit_run)
    if audit_run["returncode"] != 0:
        report = {
            "generated_at": now_iso(),
            "status": "failed",
            "failed_step": "audit",
            "run_dir": str(run_dir),
            "steps": pipeline_steps,
        }
        report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        raise SystemExit("Audit step failed. See ai_oneclick_report.json for details.")

    audit_pass_csv = audit_dir / "knowledge_base_audit_pass.csv"
    recheck_cmd = [
        python,
        str(repo_root / "scripts" / "ai_review_kb.py"),
        "--input-csv",
        str(audit_pass_csv),
        "--output-dir",
        str(recheck_dir),
        "--stage",
        "recheck",
        "--min-score",
        str(args.recheck_min_score),
        "--openai-base-url",
        args.openai_base_url,
        "--openai-api-key",
        args.openai_api_key,
        "--openai-model",
        args.openai_model,
        "--openai-fallback-models",
        args.openai_fallback_models,
        "--openai-timeout",
        str(args.openai_timeout),
    ]
    if args.strict_high_risk:
        recheck_cmd.append("--strict-high-risk")

    recheck_run = run_cmd(recheck_cmd, cwd=repo_root)
    pipeline_steps["recheck"] = summarize_run(recheck_run)
    if recheck_run["returncode"] != 0:
        report = {
            "generated_at": now_iso(),
            "status": "failed",
            "failed_step": "recheck",
            "run_dir": str(run_dir),
            "steps": pipeline_steps,
        }
        report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        raise SystemExit("Recheck step failed. See ai_oneclick_report.json for details.")

    recheck_pass_csv = recheck_dir / "knowledge_base_recheck_pass.csv"

    merge_stat = {"incoming_rows": 0, "appended_rows": 0, "skipped_rows": 0}
    if not args.skip_merge:
        merge_target = Path(args.merge_into)
        if not merge_target.is_absolute():
            merge_target = (repo_root / merge_target).resolve()
        merge_stat = merge_unique(merge_target, recheck_pass_csv)

    if not args.skip_quality_gate:
        gate_cmd = [
            python,
            str(repo_root / "scripts" / "quality_gate.py"),
            "--repo-root",
            str(repo_root),
        ]
        gate_run = run_cmd(gate_cmd, cwd=repo_root)
        pipeline_steps["quality_gate"] = summarize_run(gate_run)
        if gate_run["returncode"] != 0:
            report = {
                "generated_at": now_iso(),
                "status": "failed",
                "failed_step": "quality_gate",
                "run_dir": str(run_dir),
                "merge_stat": merge_stat,
                "steps": pipeline_steps,
            }
            report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            raise SystemExit("Quality gate failed. See ai_oneclick_report.json for details.")

    if not args.skip_eval_regression:
        eval_cmd = [
            python,
            str(repo_root / "scripts" / "run_eval_regression_pipeline.py"),
            "--repo-root",
            str(repo_root),
            "--update-dashboard",
        ]
        if args.allow_skip_live_eval:
            eval_cmd.append("--allow-skip-live")
        if args.eval_limit > 0:
            eval_cmd.extend(["--limit", str(args.eval_limit)])
        eval_run = run_cmd(eval_cmd, cwd=repo_root)
        pipeline_steps["eval_regression"] = summarize_run(eval_run)
        if eval_run["returncode"] != 0:
            report = {
                "generated_at": now_iso(),
                "status": "failed",
                "failed_step": "eval_regression",
                "run_dir": str(run_dir),
                "merge_stat": merge_stat,
                "steps": pipeline_steps,
            }
            report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            raise SystemExit("Eval regression failed. See ai_oneclick_report.json for details.")

    audit_report = load_json(audit_dir / "ai_review_report_audit.json")
    recheck_report = load_json(recheck_dir / "ai_review_report_recheck.json")

    result = {
        "generated_at": now_iso(),
        "status": "success",
        "run_dir": str(run_dir),
        "input_candidate_csv": str(candidate_csv),
        "outputs": {
            "audit_pass_csv": str(audit_pass_csv),
            "recheck_pass_csv": str(recheck_pass_csv),
            "report_json": str(report_json),
            "report_md": str(report_md),
        },
        "counts": {
            "candidate_rows": count_rows(candidate_csv),
            "audit_pass_rows": count_rows(audit_pass_csv),
            "recheck_pass_rows": count_rows(recheck_pass_csv),
        },
        "merge_stat": merge_stat,
        "ai": {
            "audit": audit_report,
            "recheck": recheck_report,
        },
        "steps": pipeline_steps,
    }
    report_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# AI One-Click Pipeline Report",
        "",
        f"- Generated: `{result['generated_at']}`",
        f"- Run dir: `{run_dir}`",
        f"- Candidate rows: `{result['counts']['candidate_rows']}`",
        f"- Audit pass rows: `{result['counts']['audit_pass_rows']}`",
        f"- Recheck pass rows: `{result['counts']['recheck_pass_rows']}`",
        f"- Merge appended rows: `{merge_stat['appended_rows']}`",
        "",
        "## Outputs",
        f"- audit pass: `{audit_pass_csv}`",
        f"- recheck pass: `{recheck_pass_csv}`",
        f"- report json: `{report_json}`",
        "",
    ]
    report_md.write_text("\n".join(lines), encoding="utf-8")

    print(f"AI one-click run done: {run_dir}")
    print(f"- report: {report_json}")
    print(f"- appended rows: {merge_stat['appended_rows']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

