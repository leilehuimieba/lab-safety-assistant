#!/usr/bin/env python3
"""本地知识库检索效果对比脚本

对比纯文本检索（token 匹配）与混合检索（bge-m3 语义 + token 匹配）的召回差异。
运行前需确保已安装 sentence-transformers 并首次构建好索引：

    pip install -r requirements.txt
    python -c "from web_demo.services.kb_service import retrieve_citations; retrieve_citations('test')"

用法：
    # 使用 eval_set_v1.csv 全量评估
    python scripts/eval_kb_retrieval.py

    # 只测指定问题
    python scripts/eval_kb_retrieval.py --questions "实验室着火怎么办" "液氮如何安全使用"

    # 调整语义权重后对比（默认 8.0）
    python scripts/eval_kb_retrieval.py --semantic-weight 12.0 --questions "有人触电了怎么办"
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# 必须在修改环境变量之前导入，否则 _EMBEDDING_AVAILABLE 在导入后即固定
import web_demo.services.kb_service as _kb_svc  # noqa: E402
from web_demo.services.kb_service import retrieve_citations  # noqa: E402


def _fetch(question: str, top_k: int, enable_embedding: bool) -> list[dict]:
    os.environ["ENABLE_EMBEDDING"] = "1" if enable_embedding else "0"
    citations = retrieve_citations(question, top_k=top_k)
    return [c.model_dump() for c in citations]


def _fmt(c: dict) -> str:
    return f"{c['kb_id']}({c['score']:.2f})"


def _load_eval_questions(path: Path) -> list[str]:
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [row["question"] for row in reader if row.get("question", "").strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="对比纯文本检索与 bge-m3 混合检索")
    parser.add_argument("--questions", nargs="+", help="指定要测试的问题（默认读取 eval_set_v1.csv）")
    parser.add_argument("--top-k", type=int, default=5, help="返回条数（默认 5）")
    parser.add_argument("--semantic-weight", type=float, default=None, help="临时调整语义权重（默认使用环境变量 SEMANTIC_WEIGHT 或 8.0）")
    parser.add_argument("--output", type=Path, default=None, help="输出 CSV 报告路径")
    args = parser.parse_args()

    questions = args.questions
    if not questions:
        eval_path = ROOT / "eval_set_v1.csv"
        if eval_path.exists():
            questions = _load_eval_questions(eval_path)
        else:
            print(f"未找到 {eval_path}，请用 --questions 指定问题")
            sys.exit(1)

    if args.semantic_weight is not None:
        _kb_svc._SEMANTIC_WEIGHT = args.semantic_weight
        print(f"[INFO] 临时语义权重调整为: {_kb_svc._SEMANTIC_WEIGHT}")

    print(f"共评估 {len(questions)} 个问题，Top K = {args.top_k}")
    print("=" * 90)

    rows: list[dict] = []
    improved = 0
    degraded = 0
    unchanged = 0

    for q in questions:
        text_res = _fetch(q, args.top_k, enable_embedding=False)
        hybrid_res = _fetch(q, args.top_k, enable_embedding=True)

        text_ids = [c["kb_id"] for c in text_res]
        hybrid_ids = [c["kb_id"] for c in hybrid_res]
        text_set = set(text_ids)
        hybrid_set = set(hybrid_ids)

        new_ids = hybrid_set - text_set
        lost_ids = text_set - hybrid_set

        # 简单启发式判断改善/退化：看 Top-1 是否变化
        text_top1 = text_ids[0] if text_ids else ""
        hybrid_top1 = hybrid_ids[0] if hybrid_ids else ""

        if text_top1 and hybrid_top1 and text_top1 != hybrid_top1:
            changed = "changed"
        elif text_top1 == hybrid_top1:
            changed = "same"
        else:
            changed = "unknown"

        if new_ids and not lost_ids:
            improved += 1
        elif lost_ids and not new_ids:
            degraded += 1
        else:
            unchanged += 1

        print(f"\n问题: {q}")
        print(f"  纯文本 Top-{args.top_k}: {' | '.join(_fmt(c) for c in text_res)}")
        print(f"  混合检索 Top-{args.top_k}: {' | '.join(_fmt(c) for c in hybrid_res)}")
        if new_ids:
            print(f"  [混合新增] {', '.join(sorted(new_ids))}")
        if lost_ids:
            print(f"  [混合丢失] {', '.join(sorted(lost_ids))}")
        print(f"  Top-1 变化: {changed}")

        rows.append(
            {
                "question": q,
                "text_top1": text_top1,
                "hybrid_top1": hybrid_top1,
                "text_topk": " | ".join(text_ids),
                "hybrid_topk": " | ".join(hybrid_ids),
                "new_in_hybrid": ", ".join(sorted(new_ids)),
                "lost_in_hybrid": ", ".join(sorted(lost_ids)),
            }
        )

    print("\n" + "=" * 90)
    print(f"统计: 改善(新增未丢)={improved}, 退化(丢失未增)={degraded}, 其他={unchanged}")

    if args.output:
        with open(args.output, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "question",
                    "text_top1",
                    "hybrid_top1",
                    "text_topk",
                    "hybrid_topk",
                    "new_in_hybrid",
                    "lost_in_hybrid",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)
        print(f"报告已保存: {args.output}")


if __name__ == "__main__":
    main()
