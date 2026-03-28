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
        description="Temporarily patch workflow to minimal start->llm->answer or restore from backup."
    )
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument("--workflow-id", required=True, help="Target workflow id.")
    parser.add_argument(
        "--mode",
        choices=["apply-minimal", "restore"],
        default="apply-minimal",
        help="Patch mode.",
    )
    parser.add_argument(
        "--backup-file",
        default="",
        help="Backup graph json file (required for restore).",
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


def build_minimal_graph(source_obj: dict) -> dict:
    nodes = list(source_obj.get("nodes") or [])
    start_node = None
    llm_node = None
    answer_node = None
    for node in nodes:
        data = node.get("data") or {}
        node_type = str(data.get("type") or "")
        if node_type == "start" and start_node is None:
            start_node = node
        elif node_type == "llm" and llm_node is None:
            llm_node = node
        elif node_type == "answer" and answer_node is None:
            answer_node = node

    start_id = str((start_node or {}).get("id") or "start_minimal")
    llm_id = str((llm_node or {}).get("id") or "llm_minimal")
    answer_id = str((answer_node or {}).get("id") or "answer_minimal")

    llm_model = {
        "provider": "langgenius/openai_api_compatible/openai_api_compatible",
        "name": "gpt-5.2-codex",
        "mode": "chat",
        "completion_params": {"temperature": 0.2},
    }
    if llm_node:
        model_from_source = (llm_node.get("data") or {}).get("model")
        if isinstance(model_from_source, dict):
            llm_model.update(model_from_source)
            llm_model["completion_params"] = {"temperature": 0.2}

    minimal_nodes = [
        {
            "id": start_id,
            "type": "custom",
            "data": {
                "variables": [],
                "type": "start",
                "title": "用户输入",
                "selected": False,
            },
            "position": {"x": 80, "y": 360},
            "targetPosition": "left",
            "sourcePosition": "right",
            "width": 242,
            "height": 72,
            "selected": False,
        },
        {
            "id": llm_id,
            "type": "custom",
            "data": {
                "model": llm_model,
                "prompt_template": [
                    {
                        "role": "system",
                        "text": (
                            "你是实验室安全助手。"
                            "请用简洁、可执行的步骤回答。"
                            "若请求涉及危险或违规操作，必须拒绝并给出安全替代建议。"
                        ),
                        "id": "minimal-system",
                    },
                    {
                        "role": "user",
                        "text": "问题：{{#sys.query#}}",
                        "id": "minimal-user",
                    },
                ],
                "context": {"enabled": False, "variable_selector": []},
                "vision": {"enabled": False},
                "type": "llm",
                "title": "LLM",
                "selected": False,
                "structured_output_enabled": False,
                "reasoning_format": "separated",
            },
            "position": {"x": 430, "y": 360},
            "targetPosition": "left",
            "sourcePosition": "right",
            "width": 241,
            "height": 87,
            "selected": False,
        },
        {
            "id": answer_id,
            "type": "custom",
            "data": {
                "variables": [],
                "answer": f"{{{{#{llm_id}.text#}}}}",
                "type": "answer",
                "title": "直接回复",
                "selected": False,
            },
            "position": {"x": 770, "y": 360},
            "targetPosition": "left",
            "sourcePosition": "right",
            "width": 241,
            "height": 102,
            "selected": False,
        },
    ]

    minimal_edges = [
        {
            "id": f"{start_id}-source-{llm_id}-target",
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
        },
        {
            "id": f"{llm_id}-source-{answer_id}-target",
            "type": "custom",
            "source": llm_id,
            "sourceHandle": "source",
            "target": answer_id,
            "targetHandle": "target",
            "data": {
                "sourceType": "llm",
                "targetType": "answer",
                "isInIteration": False,
                "isInLoop": False,
            },
            "zIndex": 0,
        },
    ]

    return {
        "nodes": minimal_nodes,
        "edges": minimal_edges,
        "viewport": {"x": 0, "y": 0, "zoom": 1},
    }


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()

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

    out_dir = repo_root / "artifacts" / "workflow_patches" / f"run_{now_tag()}"
    out_dir.mkdir(parents=True, exist_ok=True)

    original = fetch_graph(args)
    backup_file = out_dir / f"workflow_{args.workflow_id}_backup_before_minimal.json"
    backup_file.write_text(original, encoding="utf-8")

    src_obj = json.loads(original)
    minimal_obj = build_minimal_graph(src_obj)
    minimal_text = json.dumps(minimal_obj, ensure_ascii=False)
    patched_file = out_dir / f"workflow_{args.workflow_id}_minimal_patch.json"
    patched_file.write_text(minimal_text, encoding="utf-8")

    update_graph(args, minimal_text)
    print("Workflow patched to minimal flow.")
    print(f"- workflow_id: {args.workflow_id}")
    print(f"- backup_file: {backup_file}")
    print(f"- patched_file: {patched_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

