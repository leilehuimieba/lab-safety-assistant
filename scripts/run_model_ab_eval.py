#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def now_tag() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run A/B live regression by switching Dify workflow model names and auto-restore."
    )
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument("--app-id", required=True, help="Target Dify app id.")
    parser.add_argument("--dify-base-url", default="http://localhost:8080", help="Dify base URL.")
    parser.add_argument("--dify-app-key", default="", help="Dify app key. If empty, auto-fetch from DB.")
    parser.add_argument("--model-a", default="MiniMax-M2.5", help="Model A name in workflow llm node.")
    parser.add_argument("--model-b", default="gpt-5.2-codex", help="Model B name in workflow llm node.")
    parser.add_argument("--limit", type=int, default=6, help="Eval row limit.")
    parser.add_argument("--dify-timeout", type=float, default=30.0, help="Per request timeout for smoke.")
    parser.add_argument("--eval-concurrency", type=int, default=4, help="Concurrency for smoke calls.")
    parser.add_argument("--skip-preflight", action="store_true", help="Skip Dify /parameters preflight.")
    parser.add_argument("--skip-chat-preflight", action="store_true", help="Skip Dify /chat-messages preflight.")
    parser.add_argument("--preflight-timeout", type=float, default=8.0, help="Dify /parameters preflight timeout.")
    parser.add_argument(
        "--chat-preflight-timeout",
        type=float,
        default=20.0,
        help="Dify /chat-messages preflight timeout.",
    )
    parser.add_argument("--worker-log-container", default="docker-worker-1", help="Worker container for diagnosis.")
    parser.add_argument("--db-container", default="docker-db_postgres-1", help="Postgres container name.")
    parser.add_argument("--db-user", default="postgres", help="Postgres user.")
    parser.add_argument("--db-name", default="dify", help="Postgres database.")
    return parser.parse_args()


def run_cmd(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return completed


def run_psql_sql(args: argparse.Namespace, sql: str) -> str:
    cmd = [
        "docker",
        "exec",
        args.db_container,
        "psql",
        "-U",
        args.db_user,
        "-d",
        args.db_name,
        "-t",
        "-A",
        "-c",
        sql,
    ]
    completed = run_cmd(cmd)
    if completed.returncode != 0:
        raise RuntimeError(f"psql failed: {completed.stderr.strip() or completed.stdout.strip()}")
    return completed.stdout


def fetch_app_key(args: argparse.Namespace) -> str:
    sql = (
        "select token from api_tokens "
        f"where app_id='{args.app_id}' order by created_at desc limit 1;"
    )
    app_token_value = run_psql_sql(args, sql).strip()
    if not app_token_value:
        raise RuntimeError(f"No api_tokens found for app_id={args.app_id}")
    return app_token_value


def fetch_workflow_ids(args: argparse.Namespace) -> list[str]:
    sql = (
        "select id from workflows "
        f"where app_id='{args.app_id}' and type='chat' order by updated_at desc;"
    )
    raw = run_psql_sql(args, sql)
    ids = [line.strip() for line in raw.splitlines() if line.strip()]
    if not ids:
        raise RuntimeError(f"No workflows found for app_id={args.app_id}")
    return ids


def fetch_workflow_graph(args: argparse.Namespace, workflow_id: str) -> str:
    sql = f"select graph from workflows where id='{workflow_id}';"
    graph = run_psql_sql(args, sql)
    if not graph.strip():
        raise RuntimeError(f"Empty graph for workflow={workflow_id}")
    return graph.strip()


def update_workflow_graph(args: argparse.Namespace, workflow_id: str, graph_json_text: str) -> None:
    graph_b64 = base64.b64encode(graph_json_text.encode("utf-8")).decode("ascii")
    sql = (
        "update workflows "
        f"set graph = convert_from(decode('{graph_b64}','base64'),'UTF8'), updated_at = now() "
        f"where id='{workflow_id}';"
    )
    _ = run_psql_sql(args, sql)


def patch_graph_model(graph_text: str, model_name: str) -> str:
    obj = json.loads(graph_text)
    for node in obj.get("nodes", []):
        data = node.get("data") or {}
        if data.get("type") != "llm":
            continue
        model = data.get("model") or {}
        model["name"] = model_name
        completion_params = model.get("completion_params") or {}
        completion_params["temperature"] = 0.2
        model["completion_params"] = completion_params
        data["model"] = model
        node["data"] = data
    return json.dumps(obj, ensure_ascii=False)


def parse_live_smoke_run_dir(stdout: str) -> str:
    prefix = "Live smoke run:"
    for line in stdout.splitlines():
        if line.strip().startswith(prefix):
            return line.split(prefix, 1)[1].strip()
    raise RuntimeError(f"Cannot parse run dir from pipeline output: {stdout[-1500:]}")


def run_regression(
    repo_root: Path,
    base_url: str,
    app_key: str,
    limit: int,
    timeout_sec: float,
    concurrency: int,
    args: argparse.Namespace,
) -> tuple[str, dict]:
    cmd = [
        sys.executable,
        str(repo_root / "scripts" / "run_eval_regression_pipeline.py"),
        "--repo-root",
        str(repo_root),
        "--dify-base-url",
        base_url,
        "--dify-app-key",
        app_key,
        "--limit",
        str(limit),
        "--dify-timeout",
        str(timeout_sec),
        "--eval-concurrency",
        str(max(1, concurrency)),
        "--preflight-timeout",
        str(max(1.0, float(args.preflight_timeout))),
        "--chat-preflight-timeout",
        str(max(1.0, float(args.chat_preflight_timeout))),
        "--worker-log-container",
        args.worker_log_container,
        "--update-dashboard",
    ]
    if args.skip_preflight:
        cmd.append("--skip-preflight")
    if args.skip_chat_preflight:
        cmd.append("--skip-chat-preflight")
    completed = run_cmd(cmd, cwd=repo_root)
    if completed.returncode != 0:
        detail = (completed.stdout or "") + "\n" + (completed.stderr or "")
        raise RuntimeError(f"run_eval_regression_pipeline failed:\n{detail[-5000:]}")
    run_dir = parse_live_smoke_run_dir(completed.stdout)
    summary_path = Path(run_dir) / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    return run_dir, summary


def summarize_metrics(summary: dict) -> dict[str, float]:
    metrics = summary.get("metrics", {}) or {}
    return {
        "safety_refusal_rate": float(metrics.get("safety_refusal_rate", 0.0)),
        "emergency_pass_rate": float(metrics.get("emergency_pass_rate", 0.0)),
        "qa_pass_rate": float(metrics.get("qa_pass_rate", 0.0)),
        "coverage_rate": float(metrics.get("coverage_rate", 0.0)),
        "latency_p95_ms": float(metrics.get("latency_p95_ms", 0.0)),
    }


def pct(v: float) -> str:
    return f"{v * 100:.1f}%"


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    run_tag = now_tag()
    out_dir = repo_root / "artifacts" / "model_ab_eval" / f"run_{run_tag}"
    out_dir.mkdir(parents=True, exist_ok=True)

    app_key = args.dify_app_key.strip() or fetch_app_key(args)

    workflow_ids = fetch_workflow_ids(args)
    backup_graphs: dict[str, str] = {}
    for wid in workflow_ids:
        graph = fetch_workflow_graph(args, wid)
        backup_graphs[wid] = graph
        (out_dir / f"workflow_{wid}_backup.json").write_text(graph, encoding="utf-8")

    result = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "app_id": args.app_id,
        "base_url": args.dify_base_url,
        "limit": args.limit,
        "dify_timeout": args.dify_timeout,
        "eval_concurrency": args.eval_concurrency,
        "models": {
            "A": args.model_a,
            "B": args.model_b,
        },
        "runs": {},
    }

    try:
        for label, model_name in [("A", args.model_a), ("B", args.model_b)]:
            patched: dict[str, str] = {}
            for wid, original in backup_graphs.items():
                new_graph = patch_graph_model(original, model_name)
                patched[wid] = new_graph
                update_workflow_graph(args, wid, new_graph)
                (out_dir / f"workflow_{wid}_{label}.json").write_text(new_graph, encoding="utf-8")

            run_dir, summary = run_regression(
                repo_root=repo_root,
                base_url=args.dify_base_url,
                app_key=app_key,
                limit=args.limit,
                timeout_sec=args.dify_timeout,
                concurrency=args.eval_concurrency,
                args=args,
            )
            result["runs"][label] = {
                "model": model_name,
                "run_dir": run_dir,
                "summary": summary,
                "metrics": summarize_metrics(summary),
            }
    finally:
        for wid, original in backup_graphs.items():
            update_workflow_graph(args, wid, original)
        (out_dir / "restore_done.flag").write_text("ok\n", encoding="utf-8")

    report_json = out_dir / "model_ab_report.json"
    report_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    a = result["runs"]["A"]["metrics"]
    b = result["runs"]["B"]["metrics"]
    report_md = out_dir / "model_ab_report.md"
    lines = [
        "# 模型 A/B 回归对比报告",
        "",
        f"- 生成时间：`{result['generated_at']}`",
        f"- 应用：`{args.app_id}`",
        f"- 回归限制：`limit={args.limit}`",
        f"- 请求超时：`{args.dify_timeout}s`",
        f"- 并发：`{args.eval_concurrency}`",
        "",
        "| 指标 | A: " + args.model_a + " | B: " + args.model_b + " |",
        "|---|---:|---:|",
        f"| 安全拒答率 | {pct(a['safety_refusal_rate'])} | {pct(b['safety_refusal_rate'])} |",
        f"| 应急合格率 | {pct(a['emergency_pass_rate'])} | {pct(b['emergency_pass_rate'])} |",
        f"| 常规问答合格率 | {pct(a['qa_pass_rate'])} | {pct(b['qa_pass_rate'])} |",
        f"| 覆盖率 | {pct(a['coverage_rate'])} | {pct(b['coverage_rate'])} |",
        f"| 延迟P95(ms) | {a['latency_p95_ms']:.1f} | {b['latency_p95_ms']:.1f} |",
        "",
        f"- A 运行目录：`{result['runs']['A']['run_dir']}`",
        f"- B 运行目录：`{result['runs']['B']['run_dir']}`",
        "",
        "## 结论建议",
        "",
        "- 优先选择覆盖率更高、超时更少、延迟P95更低的模型通道。",
        "- 若两者都超时，应先修上游网关稳定性，再做提示词与知识库质量调优。",
    ]
    report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"A/B report written:")
    print(f"- {report_json}")
    print(f"- {report_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
