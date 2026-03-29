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
        description="Patch Dify workflow with structured safety guardrail prompts."
    )
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument("--workflow-id", required=True, help="Target workflow id.")
    parser.add_argument(
        "--mode",
        choices=["apply-guardrails", "restore"],
        default="apply-guardrails",
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


def build_guardrail_prompt_template() -> list[dict]:
    system_text = (
        "You are a university laboratory safety assistant.\n"
        "Priorities: safety first, direct usefulness, and policy compliance.\n\n"
        "Response rules:\n"
        "1) For normal safety Q&A, answer directly. Do not ask unnecessary follow-up questions.\n"
        "2) For dangerous, illegal, or high-risk requests, explicitly refuse to provide operational guidance. "
        "State risk briefly and provide safe alternatives.\n"
        "3) For emergency scenarios, prioritize immediate life-safety actions and escalation.\n"
        "4) Use provided context when available. If context is missing, give conservative best-practice guidance "
        "and note uncertainty.\n"
        "5) Never provide bypass, disable, or optimization tips for unsafe operations.\n\n"
        "Output must contain exactly these sections in this order:\n"
        "answer:\n"
        "steps:\n"
        "ppe:\n"
        "forbidden:\n"
        "emergency:\n\n"
        "Language rule: if the user asks in Chinese, answer in Chinese."
    )
    user_text = (
        "Question:\n"
        "{{#sys.query#}}\n\n"
        "Knowledge context (may be empty):\n"
        "{{#context#}}\n\n"
        "Please follow the required five-section format exactly."
    )
    return [
        {"role": "system", "text": system_text, "id": "guardrail-system-v1"},
        {"role": "user", "text": user_text, "id": "guardrail-user-v1"},
    ]


def patch_llm_prompt_templates(graph_obj: dict) -> tuple[int, list[str]]:
    updated = 0
    llm_ids: list[str] = []
    new_template = build_guardrail_prompt_template()
    for node in graph_obj.get("nodes", []):
        data = node.get("data") or {}
        if data.get("type") != "llm":
            continue
        data["prompt_template"] = new_template
        node["data"] = data
        llm_id = str(node.get("id") or "").strip()
        if llm_id:
            llm_ids.append(llm_id)
        updated += 1
    return updated, llm_ids


def patch_answer_binding(graph_obj: dict, llm_ids: list[str]) -> int:
    if not llm_ids:
        return 0
    primary_llm_id = llm_ids[0]
    expected_binding = f"{{{{#{primary_llm_id}.text#}}}}"
    updated = 0
    for node in graph_obj.get("nodes", []):
        data = node.get("data") or {}
        if data.get("type") != "answer":
            continue
        answer_value = str(data.get("answer") or "").strip()
        if answer_value != expected_binding:
            data["answer"] = expected_binding
            node["data"] = data
            updated += 1
    return updated


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
    backup_file = out_dir / f"workflow_{args.workflow_id}_backup_before_guardrails.json"
    backup_file.write_text(original, encoding="utf-8")

    graph_obj = json.loads(original)
    llm_updated, llm_ids = patch_llm_prompt_templates(graph_obj)
    answer_updated = patch_answer_binding(graph_obj, llm_ids)
    patched_text = json.dumps(graph_obj, ensure_ascii=False)
    patched_file = out_dir / f"workflow_{args.workflow_id}_patched_guardrails.json"
    patched_file.write_text(patched_text, encoding="utf-8")

    if llm_updated == 0:
        print("No llm node found. No update applied.")
        print(f"- backup_file: {backup_file}")
        print(f"- patched_file: {patched_file}")
        return 0

    update_graph(args, patched_text)
    print("Workflow guardrail prompt patched.")
    print(f"- workflow_id: {args.workflow_id}")
    print(f"- llm_nodes_updated: {llm_updated}")
    print(f"- answer_nodes_rebound: {answer_updated}")
    print(f"- backup_file: {backup_file}")
    print(f"- patched_file: {patched_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
