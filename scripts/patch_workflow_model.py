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
    parser = argparse.ArgumentParser(description="Patch Dify workflow llm model name with backup.")
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument("--workflow-id", required=True, help="Target workflow id.")
    parser.add_argument("--model-name", required=True, help="Target model name for llm nodes.")
    parser.add_argument("--temperature", type=float, default=0.2, help="LLM temperature.")
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


def patch_model(graph_obj: dict, model_name: str, temperature: float) -> int:
    changed = 0
    for node in graph_obj.get("nodes", []):
        data = node.get("data") or {}
        if data.get("type") != "llm":
            continue
        model = data.get("model") or {}
        model["name"] = model_name
        completion_params = model.get("completion_params") or {}
        completion_params["temperature"] = temperature
        model["completion_params"] = completion_params
        data["model"] = model
        node["data"] = data
        changed += 1
    return changed


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    out_dir = repo_root / "artifacts" / "workflow_patches" / f"run_{now_tag()}"
    out_dir.mkdir(parents=True, exist_ok=True)

    original = fetch_graph(args)
    backup_file = out_dir / f"workflow_{args.workflow_id}_backup_before_model_patch.json"
    backup_file.write_text(original, encoding="utf-8")

    obj = json.loads(original)
    changed = patch_model(obj, args.model_name, args.temperature)
    patched_text = json.dumps(obj, ensure_ascii=False)
    patched_file = out_dir / f"workflow_{args.workflow_id}_patched_model_{args.model_name}.json"
    patched_file.write_text(patched_text, encoding="utf-8")

    if changed == 0:
        print("No llm node found. No update applied.")
        print(f"- backup_file: {backup_file}")
        print(f"- patched_file: {patched_file}")
        return 0

    update_graph(args, patched_text)
    print("Workflow model patched.")
    print(f"- workflow_id: {args.workflow_id}")
    print(f"- model_name: {args.model_name}")
    print(f"- llm_nodes_updated: {changed}")
    print(f"- backup_file: {backup_file}")
    print(f"- patched_file: {patched_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

