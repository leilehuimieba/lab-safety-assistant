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
        description="Patch Dify workflow retrieval nodes (disable/restore) with backup."
    )
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument("--workflow-id", required=True, help="Target workflow id.")
    parser.add_argument(
        "--mode",
        choices=["disable-retrieval", "restore"],
        default="disable-retrieval",
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


def fetch_workflow_graph(args: argparse.Namespace) -> str:
    sql = f"select graph from workflows where id='{args.workflow_id}';"
    graph = run_psql_sql(args, sql)
    if not graph:
        raise RuntimeError(f"Workflow graph empty or not found: {args.workflow_id}")
    return graph


def update_workflow_graph(args: argparse.Namespace, graph_json_text: str) -> None:
    graph_b64 = base64.b64encode(graph_json_text.encode("utf-8")).decode("ascii")
    sql = (
        "update workflows "
        f"set graph = convert_from(decode('{graph_b64}','base64'),'UTF8'), updated_at = now() "
        f"where id='{args.workflow_id}';"
    )
    _ = run_psql_sql(args, sql)


def patch_disable_retrieval(graph_obj: dict) -> tuple[dict, list[str], int]:
    nodes = list(graph_obj.get("nodes") or [])
    edges = list(graph_obj.get("edges") or [])

    retrieval_ids: list[str] = []
    start_ids: list[str] = []
    llm_ids: list[str] = []
    for node in nodes:
        node_id = str(node.get("id") or "")
        data = node.get("data") or {}
        node_type = str(data.get("type") or "")
        if node_type == "knowledge-retrieval":
            retrieval_ids.append(node_id)
        if node_type == "start":
            start_ids.append(node_id)
        if node_type == "llm":
            llm_ids.append(node_id)

    if not retrieval_ids:
        return graph_obj, [], 0

    nodes = [node for node in nodes if str(node.get("id") or "") not in set(retrieval_ids)]
    edges = [
        edge
        for edge in edges
        if str(edge.get("source") or "") not in set(retrieval_ids)
        and str(edge.get("target") or "") not in set(retrieval_ids)
    ]

    node_by_id = {str(node.get("id") or ""): node for node in nodes}
    added_edges = 0
    if start_ids:
        start_id = start_ids[0]
        for llm_id in llm_ids:
            node = node_by_id.get(llm_id)
            if not node:
                continue
            data = node.get("data") or {}
            ctx = data.get("context") or {}
            variable_selector = ctx.get("variable_selector")
            if isinstance(variable_selector, list) and variable_selector:
                if str(variable_selector[0]) in set(retrieval_ids):
                    ctx["enabled"] = False
                    ctx["variable_selector"] = []
                    data["context"] = ctx
                    node["data"] = data
            has_incoming = any(str(edge.get("target") or "") == llm_id for edge in edges)
            if not has_incoming:
                edge_id = f"{start_id}-source-{llm_id}-target"
                edges.append(
                    {
                        "id": edge_id,
                        "type": "custom",
                        "source": start_id,
                        "sourceHandle": "source",
                        "target": llm_id,
                        "targetHandle": "target",
                        "data": {
                            "sourceType": "start",
                            "targetType": "llm",
                            "isInIteration": False,
                            "isInLoop": False,
                        },
                        "zIndex": 0,
                    }
                )
                added_edges += 1

    graph_obj["nodes"] = nodes
    graph_obj["edges"] = edges
    return graph_obj, retrieval_ids, added_edges


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    patch_dir = repo_root / "artifacts" / "workflow_patches" / f"run_{now_tag()}"
    patch_dir.mkdir(parents=True, exist_ok=True)

    if args.mode == "restore":
        backup_file = Path(args.backup_file).resolve()
        if not backup_file.exists():
            raise RuntimeError(f"Backup file not found: {backup_file}")
        backup_graph = backup_file.read_text(encoding="utf-8")
        update_workflow_graph(args, backup_graph)
        print("Workflow restored.")
        print(f"- workflow_id: {args.workflow_id}")
        print(f"- backup_file: {backup_file}")
        return 0

    original_graph_text = fetch_workflow_graph(args)
    backup_file = patch_dir / f"workflow_{args.workflow_id}_backup.json"
    backup_file.write_text(original_graph_text, encoding="utf-8")

    graph_obj = json.loads(original_graph_text)
    patched_obj, retrieval_ids, added_edges = patch_disable_retrieval(graph_obj)
    patched_text = json.dumps(patched_obj, ensure_ascii=False)
    patched_file = patch_dir / f"workflow_{args.workflow_id}_patched_disable_retrieval.json"
    patched_file.write_text(patched_text, encoding="utf-8")

    if not retrieval_ids:
        print("No knowledge-retrieval node found. No update applied.")
        print(f"- backup_file: {backup_file}")
        print(f"- patched_file: {patched_file}")
        return 0

    update_workflow_graph(args, patched_text)
    print("Workflow patched: retrieval disabled.")
    print(f"- workflow_id: {args.workflow_id}")
    print(f"- retrieval_nodes_removed: {','.join(retrieval_ids)}")
    print(f"- edges_added: {added_edges}")
    print(f"- backup_file: {backup_file}")
    print(f"- patched_file: {patched_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
