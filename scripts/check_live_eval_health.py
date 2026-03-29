#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import run_eval_regression_pipeline as rep


def now_tag() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pre-run health check for live eval pipeline (Dify + embedding channel)."
    )
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument("--dify-base-url", default="", help="Dify base URL (or env DIFY_BASE_URL).")
    parser.add_argument("--dify-app-key", default="", help="Dify app key (or env DIFY_APP_API_KEY).")
    parser.add_argument("--response-mode", choices=["streaming", "blocking"], default="streaming")
    parser.add_argument("--preflight-timeout", type=float, default=8.0, help="Dify /parameters timeout seconds.")
    parser.add_argument(
        "--chat-preflight-timeout",
        type=float,
        default=20.0,
        help="Dify /chat-messages timeout seconds.",
    )
    parser.add_argument(
        "--worker-log-container",
        default="docker-worker-1",
        help="Worker container for log-based diagnosis hints.",
    )
    parser.add_argument(
        "--embedding-containers",
        nargs="+",
        default=["docker-api-1", "docker-worker-1", "docker-plugin_daemon-1"],
        help="Containers that must reach embedding endpoint.",
    )
    parser.add_argument("--embedding-host", default="host.docker.internal", help="Embedding host alias.")
    parser.add_argument("--embedding-port", type=int, default=11434, help="Embedding endpoint port.")
    parser.add_argument("--embedding-timeout", type=float, default=3.0, help="Embedding curl timeout seconds.")
    parser.add_argument("--skip-embedding-check", action="store_true", help="Skip embedding channel checks.")
    parser.add_argument(
        "--allow-chat-timeout-pass",
        action="store_true",
        help="Allow health check pass when only chat preflight timed out (canary will verify real traffic).",
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/live_health",
        help="Health check output root dir.",
    )
    return parser.parse_args()


def run_cmd(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def check_embedding_channel(
    *,
    repo_root: Path,
    container: str,
    host_alias: str,
    port: int,
    timeout_sec: float,
) -> tuple[bool, str]:
    if not container.strip():
        return False, "empty_container_name"
    timeout_arg = max(1.0, float(timeout_sec))
    url = f"http://{host_alias}:{port}/api/tags"
    cmd = [
        "docker",
        "exec",
        container.strip(),
        "sh",
        "-lc",
        f"curl -sS -m {timeout_arg:.1f} {url}",
    ]
    completed = run_cmd(cmd, cwd=repo_root)
    output = ((completed.stdout or "") + "\n" + (completed.stderr or "")).strip()
    if completed.returncode != 0:
        detail = output[:220] if output else "curl_failed"
        return False, f"curl_exit_{completed.returncode}: {detail}"

    lowered = output.lower()
    if "models" in lowered or "\"model\"" in lowered or "\"embeddings\"" in lowered:
        return True, output[:220]
    return False, f"unexpected_response: {output[:220]}"


def write_report(report_path: Path, payload: dict) -> None:
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path = report_path.with_suffix(".md")
    lines = [
        "# Live Eval Health Check Report",
        "",
        f"- generated_at: `{payload.get('generated_at', '')}`",
        f"- pass: `{payload.get('pass', False)}`",
        f"- pass_effective: `{payload.get('pass_effective', False)}`",
        f"- dify_base_url: `{payload.get('dify_base_url', '')}`",
        "",
        "## Checks",
        "",
        f"- parameters_preflight: `{payload.get('checks', {}).get('parameters_preflight', {}).get('ok', False)}`",
        f"- chat_preflight: `{payload.get('checks', {}).get('chat_preflight', {}).get('ok', False)}`",
        f"- embedding_check: `{payload.get('checks', {}).get('embedding', {}).get('ok', False)}`",
    ]
    hints = payload.get("hints", []) or []
    if hints:
        lines.append("")
        lines.append("## Hints")
        lines.append("")
        for item in hints:
            lines.append(f"- {item}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    output_root = (repo_root / args.output_dir).resolve() / f"run_{now_tag()}"
    output_root.mkdir(parents=True, exist_ok=True)

    dify_base_url = args.dify_base_url.strip() or os.environ.get("DIFY_BASE_URL", "").strip()
    dify_app_key = args.dify_app_key.strip() or os.environ.get("DIFY_APP_API_KEY", "").strip()
    if not dify_base_url or not dify_app_key:
        raise SystemExit("Missing DIFY_BASE_URL or DIFY_APP_API_KEY.")

    parameters_ok, parameters_detail = rep.preflight_dify(
        dify_base_url,
        dify_app_key,
        max(1.0, float(args.preflight_timeout)),
    )
    chat_ok, chat_detail = rep.preflight_dify_chat(
        dify_base_url,
        dify_app_key,
        max(1.0, float(args.chat_preflight_timeout)),
        args.response_mode,
    )

    embedding_details: list[dict[str, object]] = []
    embedding_ok = True
    if not args.skip_embedding_check:
        for container in args.embedding_containers:
            ok, detail = check_embedding_channel(
                repo_root=repo_root,
                container=container,
                host_alias=args.embedding_host,
                port=int(args.embedding_port),
                timeout_sec=max(1.0, float(args.embedding_timeout)),
            )
            embedding_details.append({"container": container, "ok": ok, "detail": detail})
            if not ok:
                embedding_ok = False
    else:
        embedding_details.append({"container": "(skipped)", "ok": True, "detail": "embedding check skipped"})

    chat_timeout_detected = (not chat_ok) and (
        "timed out" in chat_detail.lower() or "chat timeout" in chat_detail.lower()
    )
    effective_chat_ok = bool(chat_ok or (args.allow_chat_timeout_pass and chat_timeout_detected))
    hints = rep.collect_worker_log_hints(args.worker_log_container)
    passed = bool(parameters_ok and chat_ok and embedding_ok)
    pass_effective = bool(parameters_ok and effective_chat_ok and embedding_ok)
    report = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "pass": passed,
        "pass_effective": pass_effective,
        "dify_base_url": dify_base_url,
        "checks": {
            "parameters_preflight": {"ok": parameters_ok, "detail": parameters_detail},
            "chat_preflight": {
                "ok": chat_ok,
                "effective_ok": effective_chat_ok,
                "detail": chat_detail,
                "chat_timeout_detected": chat_timeout_detected,
            },
            "embedding": {"ok": embedding_ok, "details": embedding_details},
        },
        "hints": hints,
    }
    report_path = output_root / "health_check_report.json"
    write_report(report_path, report)
    print(f"Health check report: {report_path}")

    if not pass_effective:
        print("Health check failed.")
        return 2
    if passed:
        print("Health check passed.")
    else:
        print("Health check passed with chat-timeout override.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
