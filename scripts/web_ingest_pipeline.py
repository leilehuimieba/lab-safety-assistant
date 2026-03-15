#!/usr/bin/env python3
"""
Fetch public web pages, clean their main content, and export a CSV that matches
the project's knowledge base schema.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin

try:
    import httpx
    from bs4 import BeautifulSoup
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Missing dependencies. Run: pip install -r scripts/requirements-web-ingest.txt"
    ) from exc


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

REMOVE_SELECTORS = [
    "script",
    "style",
    "noscript",
    "svg",
    "canvas",
    "iframe",
    "header",
    "footer",
    "nav",
    "aside",
    "form",
    "button",
    ".breadcrumb",
    ".breadcrumbs",
    ".sidebar",
    ".share",
    ".tools",
    ".toolbar",
    ".copyright",
]

CONTENT_SELECTORS = [
    "main article",
    "article",
    "[role='main']",
    "main",
    ".article-content",
    ".entry-content",
    ".post-content",
    ".content",
    ".article",
    ".detail",
    ".show-content",
    "#content",
    "#article",
    ".news-content",
    ".read",
    "body",
]

NOISE_PATTERNS = [
    r"^首页$",
    r".*首页$",
    r"^当前位置",
    r"^上一篇",
    r"^下一篇",
    r"^打印$",
    r"^关闭窗口$",
    r"^返回顶部$",
    r"^版权所有",
    r"^Copyright",
    r"^浏览次数",
    r"^点击数",
    r"^浏览量[:：]?$",
    r"^地址[:：]",
    r"^电话[:：]",
    r"^邮箱[:：]",
]

REDIRECT_PATTERNS = [
    r'window\.location\.replace\("([^"]+)"\)',
    r'window\.location\.href\s*=\s*"([^"]+)"',
    r"URL='([^']+)'",
    r'URL="([^"]+)"',
]

KB_FIELDNAMES = [
    "id",
    "title",
    "category",
    "subcategory",
    "lab_type",
    "risk_level",
    "hazard_types",
    "scenario",
    "question",
    "answer",
    "steps",
    "ppe",
    "forbidden",
    "disposal",
    "first_aid",
    "emergency",
    "legal_notes",
    "references",
    "source_type",
    "source_title",
    "source_org",
    "source_version",
    "source_date",
    "source_url",
    "last_updated",
    "reviewer",
    "status",
    "tags",
    "language",
]


@dataclass
class SourceRow:
    source_id: str
    title: str
    source_org: str
    category: str
    subcategory: str
    lab_type: str
    risk_level: str
    hazard_types: str
    url: str
    tags: str
    language: str
    question_hint: str


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_manifest(path: Path) -> list[SourceRow]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows: list[SourceRow] = []
        for raw in reader:
            rows.append(
                SourceRow(
                    source_id=(raw.get("source_id") or "").strip(),
                    title=(raw.get("title") or "").strip(),
                    source_org=(raw.get("source_org") or "").strip(),
                    category=(raw.get("category") or "通用").strip(),
                    subcategory=(raw.get("subcategory") or "网页资料").strip(),
                    lab_type=(raw.get("lab_type") or "通用").strip(),
                    risk_level=(raw.get("risk_level") or "3").strip(),
                    hazard_types=(raw.get("hazard_types") or "").strip(),
                    url=(raw.get("url") or "").strip(),
                    tags=(raw.get("tags") or "").strip(),
                    language=(raw.get("language") or "zh-CN").strip(),
                    question_hint=(raw.get("question_hint") or "").strip(),
                )
            )
    return rows


def sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def extract_redirect_target(html: str, base_url: str) -> str | None:
    for pattern in REDIRECT_PATTERNS:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return urljoin(base_url, match.group(1))
    return None


def clean_line(line: str) -> str:
    line = re.sub(r"\s+", " ", line).strip()
    return line


def is_noise_line(line: str) -> bool:
    if len(line) <= 1:
        return True
    for pattern in NOISE_PATTERNS:
        if re.search(pattern, line, re.IGNORECASE):
            return True
    return False


def normalize_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    raw_lines = [clean_line(line) for line in text.splitlines()]
    lines: list[str] = []
    seen: set[str] = set()
    for line in raw_lines:
        if not line or is_noise_line(line):
            continue
        if line in seen:
            continue
        seen.add(line)
        lines.append(line)
    joined = "\n".join(lines)
    joined = re.sub(r"\n{3,}", "\n\n", joined)
    return joined.strip()


def extract_title(soup: BeautifulSoup, fallback: str) -> str:
    selectors = [
        ("meta", {"property": "og:title"}),
        ("meta", {"name": "title"}),
        ("title", {}),
        ("h1", {}),
    ]
    for tag_name, attrs in selectors:
        node = soup.find(tag_name, attrs=attrs)
        if not node:
            continue
        if tag_name == "meta":
            content = (node.get("content") or "").strip()
            if content:
                return content
        else:
            text = node.get_text(" ", strip=True)
            if text:
                return text
    return fallback


def extract_description(soup: BeautifulSoup, fallback_text: str) -> str:
    meta = soup.find("meta", attrs={"name": "description"}) or soup.find(
        "meta", attrs={"property": "og:description"}
    )
    if meta:
        content = (meta.get("content") or "").strip()
        if content:
            return content
    return fallback_text[:160]


def extract_publish_date(soup: BeautifulSoup, text: str) -> str:
    meta = soup.find("meta", attrs={"property": "article:published_time"}) or soup.find(
        "meta", attrs={"name": "publishdate"}
    )
    if meta:
        content = (meta.get("content") or "").strip()
        if content:
            return content

    time_node = soup.find("time")
    if time_node:
        content = (time_node.get("datetime") or time_node.get_text(" ", strip=True)).strip()
        if content:
            return content

    patterns = [
        r"(20\d{2}-\d{2}-\d{2})",
        r"(20\d{2}/\d{2}/\d{2})",
        r"(20\d{2}年\d{1,2}月\d{1,2}日)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return ""


def find_best_content_node(soup: BeautifulSoup):
    def node_score(node) -> float:
        text = normalize_text(node.get_text("\n", strip=True))
        if not text:
            return 0
        link_text = normalize_text(" ".join(a.get_text(" ", strip=True) for a in node.find_all("a")))
        short_lines = sum(
            1
            for line in text.splitlines()
            if line.strip() and len(line.strip()) <= 8 and not re.search(r"[。；：:，,]", line)
        )
        return len(text) - (len(link_text) * 1.5) - (len(node.find_all("a")) * 40) - (short_lines * 30)

    best_node = None
    best_score = 0.0
    for selector in CONTENT_SELECTORS:
        for node in soup.select(selector):
            score = node_score(node)
            if score > best_score:
                best_node = node
                best_score = score
    return best_node or soup.body or soup


def extract_main_text(html: str) -> tuple[str, str, str]:
    soup = BeautifulSoup(html, "html.parser")
    for selector in REMOVE_SELECTORS:
        for node in soup.select(selector):
            node.decompose()

    best_node = find_best_content_node(soup)
    main_text = normalize_text(best_node.get_text("\n", strip=True))
    title = extract_title(soup, fallback="")
    description = extract_description(soup, fallback_text=main_text)
    return title, description, main_text


def split_into_chunks(text: str, max_chars: int, overlap: int) -> list[str]:
    paragraphs = [item.strip() for item in text.split("\n") if item.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if not current:
            current = paragraph
            continue
        candidate = f"{current}\n{paragraph}"
        if len(candidate) <= max_chars:
            current = candidate
            continue
        chunks.append(current)
        if overlap > 0 and len(current) > overlap:
            current = current[-overlap:] + "\n" + paragraph
        else:
            current = paragraph

    if current:
        chunks.append(current)

    return [chunk.strip() for chunk in chunks if chunk.strip()]


async def fetch_source(
    client: httpx.AsyncClient,
    row: SourceRow,
    raw_dir: Path,
) -> dict:
    html_path = raw_dir / f"{row.source_id}.html"
    result = {
        "source_id": row.source_id,
        "requested_url": row.url,
        "final_url": row.url,
        "status": "error",
        "status_code": 0,
        "fetched_at": now_iso(),
        "html_path": str(html_path),
        "error": "",
    }

    try:
        response = await client.get(row.url, headers=DEFAULT_HEADERS, follow_redirects=True)
        html = response.text
        final_url = str(response.url)

        redirect_target = extract_redirect_target(html, final_url)
        if redirect_target and redirect_target != final_url:
            response = await client.get(
                redirect_target, headers=DEFAULT_HEADERS, follow_redirects=True
            )
            html = response.text
            final_url = str(response.url)

        html_path.write_text(html, encoding="utf-8")
        result.update(
            {
                "final_url": final_url,
                "status": "success",
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type", ""),
                "html_sha1": sha1_text(html),
            }
        )
    except Exception as exc:
        result["error"] = str(exc)

    return result


async def fetch_all(rows: list[SourceRow], raw_dir: Path, concurrency: int) -> list[dict]:
    semaphore = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient(timeout=20.0) as client:
        async def runner(row: SourceRow) -> dict:
            async with semaphore:
                return await fetch_source(client, row, raw_dir)

        tasks = [runner(row) for row in rows]
        return await asyncio.gather(*tasks)


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_clean_documents(rows: list[SourceRow], fetch_results: list[dict]) -> list[dict]:
    row_by_id = {row.source_id: row for row in rows}
    documents: list[dict] = []
    for item in fetch_results:
        if item.get("status") != "success":
            continue
        source_row = row_by_id[item["source_id"]]
        html = Path(item["html_path"]).read_text(encoding="utf-8")
        title, description, main_text = extract_main_text(html)
        if len(main_text) < 120:
            continue

        published_date = extract_publish_date(BeautifulSoup(html, "html.parser"), main_text)
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
                    "legal_notes": "基于公开网页资料自动抽取，导入知识库前请人工复核。",
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


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=KB_FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def merge_into_csv(path: Path, new_rows: list[dict]) -> int:
    existing_rows: list[dict] = []
    existing_ids: set[str] = set()

    if path.exists():
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                normalized = {field: row.get(field, "") for field in KB_FIELDNAMES}
                existing_rows.append(normalized)
                existing_ids.add(normalized["id"])

    appended = 0
    for row in new_rows:
        if row["id"] in existing_ids:
            continue
        existing_rows.append({field: row.get(field, "") for field in KB_FIELDNAMES})
        existing_ids.add(row["id"])
        appended += 1

    write_csv(path, existing_rows)
    return appended


def write_report(path: Path, fetch_results: list[dict], documents: list[dict], kb_rows: list[dict]) -> None:
    report = {
        "generated_at": now_iso(),
        "requested_pages": len(fetch_results),
        "fetched_successfully": sum(1 for item in fetch_results if item.get("status") == "success"),
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
    return parser.parse_args()


def main() -> None:
    asyncio.run(run_pipeline(parse_args()))


if __name__ == "__main__":
    main()
