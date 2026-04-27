#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def now_tag() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Tune Dify workflow for lower latency (retrieval top_k / llm max_tokens) with backup."
    )
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument("--workflow-id", required=True, help="Target workflow id.")
    parser.add_argument(
        "--mode",
        choices=["apply-latency", "restore"],
        default="apply-latency",
        help="Patch mode.",
    )
    parser.add_argument(
        "--backup-file",
        default="",
        help="Backup graph JSON path (required for restore mode).",
    )
    parser.add_argument("--retrieval-top-k", type=int, default=3, help="Top-K for retrieval node.")
    parser.add_argument(
        "--llm-max-tokens",
        type=int,
        default=900,
        help="max_tokens in llm completion_params.",
    )
    parser.add_argument("--db-container", default="docker-db_postgres-1", help="Postgres container.")
    parser.add_argument("--db-user", default="postgres", help="Postgres user.")
    parser.add_argument("--db-name", default="dify", help="Postgres database.")
    return parser.parse_args()


def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


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
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
    return completed.stdout.strip()


def fetch_graph(args: argparse.Namespace) -> str:
    sql = f"select graph from workflows where id='{args.workflow_id}';"
    graph = run_psql_sql(args, sql)
    if not graph:
        raise RuntimeError(f"Workflow graph empty or not found: {args.workflow_id}")
    return graph


def update_graph(args: argparse.Namespace, graph_json_text: str) -> None:
    graph_b64 = base64.b64encode(graph_json_text.encode("utf-8")).decode("ascii")
    sql = (
        "update workflows "
        f"set graph = convert_from(decode('{graph_b64}','base64'),'UTF8'), updated_at = now() "
        f"where id='{args.workflow_id}';"
    )
    _ = run_psql_sql(args, sql)


def patch_latency(graph_obj: dict, retrieval_top_k: int, llm_max_tokens: int) -> tuple[int, int]:
    retrieval_updated = 0
    llm_updated = 0
    for node in graph_obj.get("nodes", []):
        data = node.get("data") or {}
        node_type = data.get("type")
        if node_type == "knowledge-retrieval":
            cfg = data.get("multiple_retrieval_config") or {}
            cfg["top_k"] = max(1, retrieval_top_k)
            cfg["reranking_enable"] = False
            data["multiple_retrieval_config"] = cfg
            node["data"] = data
            retrieval_updated += 1
        elif node_type == "llm":
            model = data.get("model") or {}
            completion_params = model.get("completion_params") or {}
            completion_params["max_tokens"] = max(256, llm_max_tokens)
            completion_params.setdefault("temperature", 0.2)
            model["completion_params"] = completion_params
            data["model"] = model
            node["data"] = data
            llm_updated += 1
    return retrieval_updated, llm_updated


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    out_dir = repo_root / "artifacts" / "workflow_patches" / f"run_{now_tag()}"
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.mode == "restore":
        backup_file = Path(args.backup_file).resolve()
        if not backup_file.exists():
            raise RuntimeError(f"Backup file not found: {backup_file}")
        backup_graph = backup_file.read_text(encoding="utf-8")
        update_graph(args, backup_graph)
        print("Workflow restored from backup.")
        print(f"- workflow_id: {args.workflow_id}")
        print(f"- backup_file: {backup_file}")
        return 0

    original = fetch_graph(args)
    backup_file = out_dir / f"workflow_{args.workflow_id}_backup_before_latency_tuning.json"
    backup_file.write_text(original, encoding="utf-8")

    graph_obj = json.loads(original)
    retrieval_updated, llm_updated = patch_latency(graph_obj, args.retrieval_top_k, args.llm_max_tokens)
    patched_text = json.dumps(graph_obj, ensure_ascii=False)
    patched_file = out_dir / f"workflow_{args.workflow_id}_patched_latency_tuning.json"
    patched_file.write_text(patched_text, encoding="utf-8")

    if retrieval_updated == 0 and llm_updated == 0:
        print("No retrieval/llm node found. No update applied.")
        print(f"- backup_file: {backup_file}")
        print(f"- patched_file: {patched_file}")
        return 0

    update_graph(args, patched_text)
    print("Workflow latency tuning patched.")
    print(f"- workflow_id: {args.workflow_id}")
    print(f"- retrieval_nodes_updated: {retrieval_updated}")
    print(f"- llm_nodes_updated: {llm_updated}")
    print(f"- retrieval_top_k: {max(1, args.retrieval_top_k)}")
    print(f"- llm_max_tokens: {max(256, args.llm_max_tokens)}")
    print(f"- backup_file: {backup_file}")
    print(f"- patched_file: {patched_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
