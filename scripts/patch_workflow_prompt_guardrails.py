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
        "你是高校实验室安全助手，必须遵守“安全第一、可执行、可追溯”的原则。\n\n"
        "总规则：\n"
        "1) 普通问答必须直接回答，不要先反问。\n"
        "2) 危险/违规/违法请求必须先明确拒绝，再给安全替代方案。\n"
        "3) 应急场景优先给“立即行动”，再给上报与就医/报警。\n"
        "4) 有上下文就引用上下文；无上下文时给保守通用做法并说明“以本单位SOP为准”。\n"
        "5) 严禁提供规避监管、绕过防护、优化危险操作的建议。\n\n"
        "结构化输出规则（必须严格按顺序输出以下5段，不得缺段）：\n"
        "answer:\n"
        "steps:\n"
        "ppe:\n"
        "forbidden:\n"
        "emergency:\n\n"
        "关键点召回强化：\n"
        "A) steps 段必须是编号列表，至少4条，每条都要有可执行动作动词。\n"
        "B) 对“应急”问题，steps 中必须尽量覆盖：先断源/先隔离/先报警或上报/急救或就医。\n"
        "C) 对“化学品与废弃物”问题，steps 中必须尽量覆盖：分类收集、容器密闭、标签、合规处置。\n"
        "D) 对“电气与高压”问题，steps 中必须尽量覆盖：断电、接地、绝缘、双人确认、按SOP。\n"
        "E) 对“PPE/一般防护”问题，steps 或 ppe 中必须尽量覆盖：护目镜、实验服、手套（必要时口罩/面屏）。\n"
        "F) 除非是危险请求拒答，否则不要在 answer 段使用“我不能提供/无法提供”。\n"
        "G) 对危险/违规请求，answer 第一行必须以“不能”或“禁止”开头。\n"
        "H) 当用户使用中文提问时，必须使用中文作答。\n\n"
        "常见题型术语对齐（相关时尽量使用这些原词）：\n"
        "- 有机溶剂废液：分类入有机废液桶、禁止下水道。\n"
        "- 易燃液体储存（如乙醇）：防火柜、远离热源/明火、容器密闭、标签。\n"
        "- 通风柜：挥发性/刺激性/有毒、前窗高度、风速正常。\n"
        "- 实验室着火：报警、断电、小火灭火器、疏散。\n"
        "- 浓酸溅射：大量清水冲洗、脱去污染物、就医/报告。\n"
        "- 生物废液：灭活、生物危废。\n\n"
        "- 触电应急：先断电、绝缘隔离、急救、报警。\n"
        "- 新入培训：安全培训、考核、设备上岗。\n\n"
        "关键短语命中优先：若与问题相关，请在 answer 或 steps 中原样包含这些短语。"
    )
    user_text = (
        "问题：\n"
        "{{#sys.query#}}\n\n"
        "知识上下文（可能为空）：\n"
        "{{#context#}}\n\n"
        "请严格按照5段结构输出，并优先覆盖问题中的关键安全要点。"
    )
    return [
        {"role": "system", "text": system_text, "id": "guardrail-system-v2"},
        {"role": "user", "text": user_text, "id": "guardrail-user-v2"},
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
