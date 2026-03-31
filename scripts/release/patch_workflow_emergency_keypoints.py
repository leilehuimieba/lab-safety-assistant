#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


BLOCK_MARKER = "[EMERGENCY_KEYPOINTS_V3]"
APPEND_BLOCK = """[EMERGENCY_KEYPOINTS_V3]
重点题型回答必须在 steps 或 emergency 段落中包含可检索的关键词锚点（按题型输出）：
1) 触电题：必须出现“先断电”“绝缘隔离”“急救”“报警”。
2) 浓酸溅到手上题：必须出现“大量清水冲洗”“脱去污染物”“就医/报告”。
3) 气瓶固定/气瓶存放题：必须出现“链条/支架固定”“远离热源”“瓶帽”。
要求：以上关键词请原样出现，不要仅用近义词替代。
"""


def now_tag() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Patch workflow prompt with emergency keypoint constraints.")
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument("--workflow-id", required=True, help="Workflow id.")
    parser.add_argument("--db-container", default="docker-db_postgres-1", help="Postgres container.")
    parser.add_argument("--db-user", default="postgres", help="Postgres user.")
    parser.add_argument("--db-name", default="dify", help="Postgres db.")
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


def run_sql(args: argparse.Namespace, sql: str) -> str:
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
    cp = run_cmd(cmd)
    if cp.returncode != 0:
        raise RuntimeError(cp.stderr.strip() or cp.stdout.strip())
    return cp.stdout.strip()


def fetch_graph(args: argparse.Namespace) -> str:
    sql = f"select graph from workflows where id='{args.workflow_id}';"
    graph = run_sql(args, sql)
    if not graph:
        raise RuntimeError(f"workflow graph not found: {args.workflow_id}")
    return graph


def update_graph(args: argparse.Namespace, graph_text: str) -> None:
    b64 = base64.b64encode(graph_text.encode("utf-8")).decode("ascii")
    sql = (
        "update workflows "
        f"set graph = convert_from(decode('{b64}','base64'),'UTF8'), updated_at = now() "
        f"where id='{args.workflow_id}';"
    )
    _ = run_sql(args, sql)


def patch_prompt_template(graph_obj: dict) -> int:
    updated = 0
    for node in graph_obj.get("nodes", []):
        data = node.get("data") or {}
        if data.get("type") != "llm":
            continue
        prompt_template = data.get("prompt_template")
        if not isinstance(prompt_template, list):
            continue

        for item in prompt_template:
            if not isinstance(item, dict):
                continue
            if str(item.get("role", "")).lower() != "system":
                continue

            text = str(item.get("text", ""))
            if BLOCK_MARKER in text:
                continue
            item["text"] = text.rstrip() + "\n\n" + APPEND_BLOCK
            updated += 1

        data["prompt_template"] = prompt_template
        node["data"] = data
    return updated


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    out_dir = repo_root / "artifacts" / "workflow_patches" / f"run_{now_tag()}"
    out_dir.mkdir(parents=True, exist_ok=True)

    original = fetch_graph(args)
    backup_file = out_dir / f"workflow_{args.workflow_id}_backup_before_emergency_keypoints.json"
    backup_file.write_text(original, encoding="utf-8")

    graph_obj = json.loads(original)
    updated = patch_prompt_template(graph_obj)
    patched_text = json.dumps(graph_obj, ensure_ascii=False)
    patched_file = out_dir / f"workflow_{args.workflow_id}_patched_emergency_keypoints.json"
    patched_file.write_text(patched_text, encoding="utf-8")

    if updated > 0:
        update_graph(args, patched_text)

    print("Workflow emergency keypoint patch done.")
    print(f"- workflow_id: {args.workflow_id}")
    print(f"- llm_system_prompts_updated: {updated}")
    print(f"- backup_file: {backup_file}")
    print(f"- patched_file: {patched_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
