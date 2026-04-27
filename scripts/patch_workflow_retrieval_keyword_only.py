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
        description="Patch Dify retrieval nodes to keyword-only weighted retrieval with backup."
    )
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument("--workflow-id", required=True, help="Target workflow id.")
    parser.add_argument(
        "--mode",
        choices=["apply-keyword-only", "restore"],
        default="apply-keyword-only",
        help="Patch mode.",
    )
    parser.add_argument(
        "--backup-file",
        default="",
        help="Backup graph JSON path (required for restore mode).",
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


def patch_keyword_only(graph_obj: dict) -> tuple[int, list[str]]:
    updated = 0
    node_ids: list[str] = []
    for node in graph_obj.get("nodes", []):
        data = node.get("data") or {}
        if data.get("type") != "knowledge-retrieval":
            continue
        cfg = data.get("multiple_retrieval_config") or {}
        weights = cfg.get("weights") or {}
        vector_setting = weights.get("vector_setting") or {}
        keyword_setting = weights.get("keyword_setting") or {}

        vector_setting["vector_weight"] = 0.0
        keyword_setting["keyword_weight"] = 1.0
        weights["weight_type"] = "customized"
        weights["vector_setting"] = vector_setting
        weights["keyword_setting"] = keyword_setting
        cfg["weights"] = weights
        cfg["reranking_mode"] = "weighted_score"
        data["multiple_retrieval_config"] = cfg
        data["retrieval_mode"] = "multiple"
        node["data"] = data

        node_id = str(node.get("id") or "").strip()
        if node_id:
            node_ids.append(node_id)
        updated += 1
    return updated, node_ids


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
    backup_file = out_dir / f"workflow_{args.workflow_id}_backup_before_keyword_only.json"
    backup_file.write_text(original, encoding="utf-8")

    graph_obj = json.loads(original)
    updated, node_ids = patch_keyword_only(graph_obj)
    patched_text = json.dumps(graph_obj, ensure_ascii=False)
    patched_file = out_dir / f"workflow_{args.workflow_id}_patched_keyword_only.json"
    patched_file.write_text(patched_text, encoding="utf-8")

    if updated == 0:
        print("No knowledge-retrieval node found. No update applied.")
        print(f"- backup_file: {backup_file}")
        print(f"- patched_file: {patched_file}")
        return 0

    update_graph(args, patched_text)
    print("Workflow retrieval patched to keyword-only weights.")
    print(f"- workflow_id: {args.workflow_id}")
    print(f"- retrieval_nodes_updated: {updated}")
    print(f"- retrieval_node_ids: {','.join(node_ids)}")
    print(f"- backup_file: {backup_file}")
    print(f"- patched_file: {patched_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
