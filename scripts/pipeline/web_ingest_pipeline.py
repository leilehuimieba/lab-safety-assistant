#!/usr/bin/env python3
"""
Web ingestion pipeline: fetch, extract, chunk, and export to knowledge-base CSV.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Allow importing sibling modules when loaded dynamically
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

try:
    from bs4 import BeautifulSoup
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Missing dependencies. Run: pip install -r scripts/requirements-web-ingest.txt"
    ) from exc

from libs.common_io import now_iso
from libs.ingest_io import (
    sha1_text,
    split_into_chunks,
    write_jsonl,
    write_csv,
    merge_into_csv,
)
from web_content_extractor import extract_main_text, extract_publish_date, extract_publish_date_from_text
from web_fetcher import (
    read_manifest, fetch_all, fetch_all_with_skill,
    SourceRow, resolve_skill_script_path, load_skill_fetcher_module,
)

def build_clean_documents(rows: list[SourceRow], fetch_results: list[dict]) -> list[dict]:
    row_by_id = {row.source_id: row for row in rows}
    documents: list[dict] = []
    for item in fetch_results:
        if item.get("status") != "success":
            continue
        source_row = row_by_id[item["source_id"]]
        provider = (item.get("provider") or "legacy_html").strip()
        main_text = (item.get("content_text") or "").strip()
        title = (item.get("title") or "").strip()
        description = ""
        published_date = ""

        if main_text:
            description = main_text[:160]
            published_date = extract_publish_date_from_text(main_text)
        else:
            html_path = (item.get("html_path") or "").strip()
            if not html_path:
                continue
            html = Path(html_path).read_text(encoding="utf-8")
            title, description, main_text = extract_main_text(html)
            if len(main_text) < 120:
                continue
            published_date = extract_publish_date(BeautifulSoup(html, "html.parser"), main_text)

        if len(main_text) < 120:
            continue

        documents.append(
            {
                "source_id": source_row.source_id,
                "source_title": source_row.title or title,
                "source_org": source_row.source_org,
                "category": source_row.category,
                "subcategory": source_row.subcategory,
                "lab_type": source_row.lab_type,
                "risk_level": source_row.risk_level,
                "hazard_types": source_row.hazard_types,
                "source_url": item["final_url"],
                "requested_url": item["requested_url"],
                "fetched_at": item["fetched_at"],
                "fetch_provider": provider,
                "quality_score": item.get("quality_score", 0.0),
                "requires_auth": item.get("requires_auth", False),
                "published_date": published_date,
                "description": description,
                "content": main_text,
                "content_preview": main_text[:240],
                "tags": source_row.tags,
                "language": source_row.language,
                "question_hint": source_row.question_hint,
            }
        )
    return documents



def build_kb_rows(
    documents: list[dict],
    max_chars: int,
    overlap: int,
) -> list[dict]:
    kb_rows: list[dict] = []
    today = datetime.now().strftime("%Y-%m-%d")
    for document in documents:
        chunks = split_into_chunks(document["content"], max_chars=max_chars, overlap=overlap)
        for idx, chunk in enumerate(chunks, start=1):
            title = document["source_title"]
            question_hint = document.get("question_hint") or title
            question = (
                question_hint
                if any(token in question_hint for token in ["哪些", "什么", "如何", "是否", "能否", "吗", "?", "？"])
                else f"{question_hint}有哪些要点？"
            )
            kb_rows.append(
                {
                    "id": f"{document['source_id']}-{idx:03d}",
                    "title": title if idx == 1 else f"{title}（片段{idx}）",
                    "category": document["category"],
                    "subcategory": document["subcategory"],
                    "lab_type": document["lab_type"],
                    "risk_level": document["risk_level"],
                    "hazard_types": document["hazard_types"],
                    "scenario": question_hint,
                    "question": question,
                    "answer": chunk,
                    "steps": "",
                    "ppe": "",
                    "forbidden": "",
                    "disposal": "",
                    "first_aid": "",
                    "emergency": "",
                    "legal_notes": (
                        "基于公开网页资料自动抽取，导入知识库前请人工复核。"
                        f"提取通道={document.get('fetch_provider', 'legacy_html')}；"
                        f"quality_score={document.get('quality_score', 0.0)}。"
                    ),
                    "references": f"{document['source_title']} | {document['source_url']}",
                    "source_type": "网页",
                    "source_title": document["source_title"],
                    "source_org": document["source_org"],
                    "source_version": "",
                    "source_date": document["published_date"],
                    "source_url": document["source_url"],
                    "last_updated": today,
                    "reviewer": "",
                    "status": "draft",
                    "tags": document["tags"],
                    "language": document["language"],
                }
            )
    return kb_rows



def write_report(path: Path, fetch_results: list[dict], documents: list[dict], kb_rows: list[dict]) -> None:
    blocked_count = sum(1 for item in fetch_results if item.get("fetch_status") == "blocked")
    provider_stat: dict[str, int] = {}
    for item in fetch_results:
        provider = str(item.get("provider", "unknown") or "unknown")
        provider_stat[provider] = provider_stat.get(provider, 0) + 1
    report = {
        "generated_at": now_iso(),
        "requested_pages": len(fetch_results),
        "fetched_successfully": sum(1 for item in fetch_results if item.get("status") == "success"),
        "blocked_pages": blocked_count,
        "providers": provider_stat,
        "clean_documents": len(documents),
        "knowledge_rows": len(kb_rows),
    }
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")



async def run_pipeline(args: argparse.Namespace) -> None:
    manifest_path = Path(args.manifest)
    output_dir = Path(args.output_dir)
    raw_dir = output_dir / "raw_html"
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    rows = read_manifest(manifest_path)
    skill_mode = args.fetcher_mode in {"auto", "skill"}
    skill_module = None
    skill_script_path = resolve_skill_script_path(args.skill_script)
    if skill_mode:
        skill_module = load_skill_fetcher_module(skill_script_path)
        if args.fetcher_mode == "skill" and skill_module is None:
            raise SystemExit(
                f"Skill fetcher not available: {skill_script_path}\n"
                "请先确保 skills/web-content-fetcher 已存在，或使用 --skill-script 指定脚本。"
            )

    providers = [
        item.strip().lower()
        for item in str(args.skill_providers).split(",")
        if item.strip()
    ]
    providers = [p for p in providers if p in {"jina", "scrapling", "direct"}]
    if not providers:
        providers = ["jina", "scrapling", "direct"]

    if skill_module is not None and args.fetcher_mode != "legacy":
        print(f"Fetch mode: skill ({skill_script_path})")
        fetch_results = await fetch_all_with_skill(
            rows,
            skill_module=skill_module,
            providers=providers,
            timeout=args.fetch_timeout,
            max_chars=args.fetch_max_chars,
            concurrency=args.concurrency,
        )
    else:
        print("Fetch mode: legacy_html")
        fetch_results = await fetch_all(rows, raw_dir=raw_dir, concurrency=args.concurrency)

    write_jsonl(output_dir / "fetch_results.jsonl", fetch_results)

    documents = build_clean_documents(rows, fetch_results)
    write_jsonl(output_dir / "clean_documents.jsonl", documents)

    kb_rows = build_kb_rows(documents, max_chars=args.max_chars, overlap=args.overlap)
    write_csv(output_dir / "knowledge_base_web.csv", kb_rows)

    if args.merge_into:
        merged_count = merge_into_csv(Path(args.merge_into), kb_rows)
        print(f"Merged rows into {Path(args.merge_into).resolve()}: {merged_count}")

    write_report(output_dir / "run_report.json", fetch_results, documents, kb_rows)

    print(f"Fetched pages: {sum(1 for item in fetch_results if item.get('status') == 'success')}/{len(fetch_results)}")
    print(f"Clean documents: {len(documents)}")
    print(f"Knowledge rows: {len(kb_rows)}")
    print(f"Output dir: {output_dir.resolve()}")



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch web pages and export cleaned knowledge-base CSV rows."
    )
    parser.add_argument(
        "--manifest",
        default="data_sources/web_seed_urls.csv",
        help="CSV manifest that lists public source URLs.",
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/web_ingest",
        help="Directory for raw HTML, cleaned JSONL, and exported CSV.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=3,
        help="Number of concurrent fetches.",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=1200,
        help="Maximum characters per exported knowledge chunk.",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=120,
        help="Character overlap between chunks.",
    )
    parser.add_argument(
        "--merge-into",
        default="",
        help="Optional path to append unique rows into an existing knowledge-base CSV.",
    )
    parser.add_argument(
        "--fetcher-mode",
        choices=["auto", "legacy", "skill"],
        default="auto",
        help="Web fetch mode: auto(优先skill), legacy(原HTML抓取), skill(强制skill抓取).",
    )
    parser.add_argument(
        "--skill-script",
        default="",
        help="Optional path to skills/web-content-fetcher/scripts/fetch_web_content.py",
    )
    parser.add_argument(
        "--skill-providers",
        default="jina,scrapling,direct",
        help="Provider order used by skill mode.",
    )
    parser.add_argument(
        "--fetch-timeout",
        type=int,
        default=20,
        help="Fetch timeout for skill provider requests.",
    )
    parser.add_argument(
        "--fetch-max-chars",
        type=int,
        default=30000,
        help="Max chars for skill fetch output before chunking.",
    )
    return parser.parse_args()



if __name__ == "__main__":
    main()
