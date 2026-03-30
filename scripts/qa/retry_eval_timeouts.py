#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import eval_smoke


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Retry failed/timeout rows from eval_smoke detailed_results and generate root-cause report."
    )
    parser.add_argument(
        "--input-detailed-results",
        required=True,
        help="Path to eval_smoke detailed_results.csv",
    )
    parser.add_argument(
        "--dify-base-url",
        default="http://localhost:8080",
        help="Dify base URL",
    )
    parser.add_argument(
        "--dify-app-key",
        default="",
        help="Dify app key (app-...)",
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/eval_timeout_retry",
        help="Output directory",
    )
    parser.add_argument(
        "--max-cases",
        type=int,
        default=20,
        help="Max failed cases to retry",
    )
    parser.add_argument(
        "--modes",
        default="streaming,blocking,streaming",
        help="Retry response modes sequence",
    )
    parser.add_argument(
        "--timeouts",
        default="180,180,240",
        help="Retry timeout seconds sequence; one-to-one aligned with --modes",
    )
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def classify_root_cause(attempts: list[dict[str, str]]) -> str:
    if not attempts:
        return "no_attempt"
    if any((a.get("success") or "") == "true" for a in attempts):
        # If first failed and later succeeded, usually queue/saturation or transient network.
        if (attempts[0].get("success") or "") != "true":
            return "transient_timeout_or_queue_pressure"
        return "unstable_but_recoverable"
    errors = " | ".join((a.get("error") or "").lower() for a in attempts)
    if "10061" in errors or "connection refused" in errors or "积极拒绝" in errors:
        return "endpoint_unreachable_or_service_down"
    if "timed out" in errors or "timeout" in errors:
        return "persistent_timeout"
    if "http_5" in errors:
        return "server_side_5xx"
    if "http_4" in errors:
        return "auth_or_request_issue"
    if "empty_stream_answer" in errors:
        return "empty_stream_response"
    return "unknown_failure"


def main() -> int:
    args = parse_args()
    if not args.dify_app_key.strip():
        raise SystemExit("Missing --dify-app-key")

    input_path = Path(args.input_detailed_results).resolve()
    if not input_path.exists():
        raise SystemExit(f"Input not found: {input_path}")

    modes = [x.strip() for x in args.modes.split(",") if x.strip()]
    timeout_values = [x.strip() for x in args.timeouts.split(",") if x.strip()]
    if len(modes) != len(timeout_values):
        raise SystemExit("--modes and --timeouts must have same length")
    timeouts = [float(x) for x in timeout_values]

    rows = read_rows(input_path)
    failed = [
        row
        for row in rows
        if (row.get("fetch_error") or "").strip()
        or (row.get("response_empty") or "").strip().lower() in {"1", "true", "yes"}
    ]
    failed = failed[: max(1, args.max_cases)]

    output_dir = Path(args.output_dir).resolve() / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True)

    retry_rows: list[dict[str, object]] = []
    case_report_rows: list[dict[str, object]] = []

    for row in failed:
        row_id = (row.get("id") or "").strip()
        question = (row.get("question") or "").strip()
        base_error = (row.get("fetch_error") or "").strip()
        base_latency = (row.get("latency_ms") or "").strip()

        attempts: list[dict[str, str]] = []
        for idx, (mode, timeout_sec) in enumerate(zip(modes, timeouts), start=1):
            answer, latency_ms, error = eval_smoke.call_dify(
                base_url=args.dify_base_url,
                app_key=args.dify_app_key,
                question=question,
                timeout_sec=timeout_sec,
                response_mode=mode,
            )
            success = bool(answer) and not error
            attempts.append(
                {
                    "attempt": str(idx),
                    "mode": mode,
                    "timeout_sec": str(timeout_sec),
                    "latency_ms": f"{latency_ms:.2f}",
                    "success": "true" if success else "false",
                    "error": error,
                    "answer_preview": (answer or "")[:160].replace("\n", " "),
                }
            )
            retry_rows.append(
                {
                    "id": row_id,
                    "question": question,
                    "baseline_fetch_error": base_error,
                    "baseline_latency_ms": base_latency,
                    **attempts[-1],
                }
            )
            if success:
                break

        cause = classify_root_cause(attempts)
        recovered = any((a.get("success") or "") == "true" for a in attempts)
        case_report_rows.append(
            {
                "id": row_id,
                "question": question,
                "baseline_fetch_error": base_error,
                "baseline_latency_ms": base_latency,
                "retry_attempts": len(attempts),
                "recovered": "true" if recovered else "false",
                "root_cause": cause,
                "last_error": (attempts[-1].get("error") or "") if attempts else "",
            }
        )

    retry_csv = output_dir / "timeout_retry_attempts.csv"
    case_csv = output_dir / "timeout_retry_case_summary.csv"
    summary_json = output_dir / "timeout_retry_summary.json"
    summary_md = output_dir / "timeout_retry_summary.md"

    with retry_csv.open("w", encoding="utf-8-sig", newline="") as f:
        fieldnames = [
            "id",
            "question",
            "baseline_fetch_error",
            "baseline_latency_ms",
            "attempt",
            "mode",
            "timeout_sec",
            "latency_ms",
            "success",
            "error",
            "answer_preview",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for item in retry_rows:
            writer.writerow(item)

    with case_csv.open("w", encoding="utf-8-sig", newline="") as f:
        fieldnames = [
            "id",
            "question",
            "baseline_fetch_error",
            "baseline_latency_ms",
            "retry_attempts",
            "recovered",
            "root_cause",
            "last_error",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for item in case_report_rows:
            writer.writerow(item)

    recovered_count = sum(1 for x in case_report_rows if str(x.get("recovered")) == "true")
    cause_counter = Counter(str(x.get("root_cause") or "") for x in case_report_rows)
    summary = {
        "generated_at": now_iso(),
        "input_detailed_results": str(input_path),
        "failed_cases_in_input": len(failed),
        "recovered_cases": recovered_count,
        "recovery_rate": (recovered_count / len(failed)) if failed else 0.0,
        "root_cause_distribution": dict(cause_counter),
        "artifacts": {
            "timeout_retry_attempts_csv": str(retry_csv),
            "timeout_retry_case_summary_csv": str(case_csv),
        },
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines: list[str] = []
    lines.append("# Timeout Retry Root-Cause Report")
    lines.append("")
    lines.append(f"- generated_at: `{summary['generated_at']}`")
    lines.append(f"- input: `{input_path}`")
    lines.append(f"- failed_cases: `{len(failed)}`")
    lines.append(f"- recovered_cases: `{recovered_count}`")
    lines.append(f"- recovery_rate: `{summary['recovery_rate']:.2%}`")
    lines.append("")
    lines.append("## Root Cause Distribution")
    lines.append("")
    lines.append("| root_cause | count |")
    lines.append("|---|---:|")
    for key, value in sorted(cause_counter.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"| {key} | {value} |")
    lines.append("")
    lines.append("## Case Summary")
    lines.append("")
    lines.append("| id | recovered | root_cause | baseline_latency_ms | last_error |")
    lines.append("|---|---|---|---:|---|")
    for item in case_report_rows:
        last_error = str(item.get("last_error") or "").replace("|", "/")
        lines.append(
            f"| {item['id']} | {item['recovered']} | {item['root_cause']} | {item['baseline_latency_ms']} | {last_error[:120]} |"
        )
    lines.append("")
    lines.append(f"- attempts_csv: `{retry_csv}`")
    lines.append(f"- case_summary_csv: `{case_csv}`")
    summary_md.write_text("\n".join(lines), encoding="utf-8")

    print(f"Timeout retry report done: {output_dir}")
    print(f"- summary_json: {summary_json}")
    print(f"- summary_md: {summary_md}")
    print(f"- recovered: {recovered_count}/{len(failed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
