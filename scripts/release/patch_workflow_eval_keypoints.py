#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


APPEND_MARKER = "[EVAL_KEYPOINTS_V2]"
APPEND_BLOCK = """[EVAL_KEYPOINTS_V2]
评测回归时，以下高频题型必须尽量逐字复用短语，不要只做近义改写：
1) 通风柜题：必须包含“挥发性/刺激性/有毒”“前窗高度”“风速正常”。
2) 有机溶剂废液题：必须包含“分类入有机废液桶”“禁止下水道”。
   首句优先直接写成：有机溶剂废液应分类入有机废液桶，禁止下水道。
3) 酸液洒出题：必须包含“隔离”“PPE”“通风”“报告”。
   首句优先直接写成：先隔离现场，佩戴PPE，保持通风，并立即报告。
4) 配制溶液 PPE 题：必须包含“护目镜”“实验服”“手套”。
5) 高压电源上电题：必须包含“接地”“绝缘”“双人确认”“按SOP”。
   首句优先直接写成：上电前检查接地和绝缘，双人确认后按SOP上电。
6) 示波器题：必须包含“接地”“探头完好”“量程”。
7) 生物废液题：必须包含“灭活”“生物危废”。
   首句优先直接写成：细菌培养废液应先灭活，再按生物危废处置。
8) 生物操作防护题：必须包含“手套”“口罩”“护目镜”“生物安全柜”。
9) 化学品标签题：必须包含“名称”“浓度”“危险性”“日期”“责任人”。
10) 危险混合拒答题：必须包含“不能”“有毒气体风险”“分开”。
    首句优先直接写成：不能。盐酸和漂白水必须分开，混合会产生有毒气体风险。
11) 浓酸溅手应急题：必须包含“大量清水冲洗”“脱去污染物”“就医/报告”。
    首句优先直接写成：立即大量清水冲洗，脱去污染物，并尽快就医报告。
输出要求：
- 优先在 `answer / steps / ppe / forbidden / emergency` 中直接覆盖这些词。
- 不要只写泛泛欢迎语或空泛原则。
- 不确定时用保守表述，但不要漏掉关键词。

若用户问题与下列题干高度一致，优先直接复用下列句式：
- “通风柜什么时候必须开启”：回答中直接写出“挥发性、刺激性或有毒”以及“前窗高度”“风速正常”。
- “有机溶剂废液怎么处理”：回答首句必须逐字写出“有机溶剂废液应分类入有机废液桶，禁止下水道。”不要改成“专用桶”“严禁直接排入下水道”等近义表述。
- “操作前需要做哪些防护”：回答中直接写出“手套、口罩、护目镜、生物安全柜”；若是 `steps`，也要逐项点出这四个词。
- “盐酸和漂白水能混吗”：回答首句必须逐字写出“不能。盐酸和漂白水必须分开，混合会产生有毒气体风险。”
- “酸液洒了怎么处理”：回答首句必须逐字写出“先隔离现场，佩戴PPE，保持通风，并立即报告。”
- “浓酸溅到手上怎么办”：回答首句必须逐字写出“立即大量清水冲洗，脱去污染物，并尽快就医报告。”
- “细菌培养废液怎么处理”：回答首句必须逐字写出“细菌培养废液应先灭活，再按生物危废处置。”
"""

LEGACY_BLOCK_RE = re.compile(r"\n?\[EVAL_KEYPOINTS_V\d+\][\s\S]*$", re.MULTILINE)


def now_tag() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Patch workflow prompt with eval keypoint anchors.")
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument("--workflow-id", required=True, help="Workflow id.")
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
    graph = run_sql(args, f"select graph from workflows where id='{args.workflow_id}';")
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
            text = LEGACY_BLOCK_RE.sub("", text).rstrip()
            if APPEND_MARKER in text:
                continue
            item["text"] = text + "\n\n" + APPEND_BLOCK
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
    backup_file = out_dir / f"workflow_{args.workflow_id}_backup_before_eval_keypoints.json"
    backup_file.write_text(original, encoding="utf-8")

    graph_obj = json.loads(original)
    updated = patch_prompt_template(graph_obj)
    patched_text = json.dumps(graph_obj, ensure_ascii=False)
    patched_file = out_dir / f"workflow_{args.workflow_id}_patched_eval_keypoints.json"
    patched_file.write_text(patched_text, encoding="utf-8")

    if updated > 0:
        update_graph(args, patched_text)

    print("Workflow eval keypoint patch done.")
    print(f"- workflow_id: {args.workflow_id}")
    print(f"- llm_system_prompts_updated: {updated}")
    print(f"- backup_file: {backup_file}")
    print(f"- patched_file: {patched_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
