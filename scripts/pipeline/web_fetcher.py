#!/usr/bin/env python3
"""
Web page fetcher with legacy HTML and skill-based fallback.

Supports httpx async fetching and optional skills/web-content-fetcher integration.
"""

from __future__ import annotations

import asyncio
import csv
import importlib.util
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

try:
    import httpx
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Missing dependencies. Run: pip install -r scripts/requirements-web-ingest.txt"
    ) from exc

from libs.common_io import now_iso
from libs.ingest_io import sha1_text

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

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

REDIRECT_PATTERNS = [
    r'window\.location\.replace\("([^"]+)"\)',
    r'window\.location\.href\s*=\s*"([^"]+)"',
    r"URL='([^']+)'",
    r'URL="([^"]+)"',
]

def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")



def resolve_skill_script_path(raw_path: str = "") -> Path:
    if raw_path:
        path = Path(raw_path)
        if path.exists():
            return path.resolve()
    return (
        Path(__file__).resolve().parents[2]
        / "skills"
        / "web-content-fetcher"
        / "scripts"
        / "fetch_web_content.py"
    ).resolve()



def load_skill_fetcher_module(script_path: Path) -> Any | None:
    if not script_path.exists():
        return None
    spec = importlib.util.spec_from_file_location("skill_web_content_fetcher", script_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    try:
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)  # type: ignore[attr-defined]
        return module
    except Exception:
        return None



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



def extract_redirect_target(html: str, base_url: str) -> str | None:
    for pattern in REDIRECT_PATTERNS:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return urljoin(base_url, match.group(1))
    return None



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
        "fetch_status": "error",
        "status_code": 0,
        "fetched_at": now_iso(),
        "html_path": str(html_path),
        "provider": "legacy_html",
        "quality_score": 0.0,
        "requires_auth": False,
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
                "fetch_status": "ok",
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



async def fetch_source_with_skill(
    row: SourceRow,
    skill_module: Any,
    providers: list[str],
    timeout: int,
    max_chars: int,
) -> dict:
    def run_sync() -> dict:
        result = skill_module.fetch_with_fallback(
            row.url,
            providers=providers,
            timeout=timeout,
            max_chars=max_chars,
        )
        payload = {
            "source_id": row.source_id,
            "requested_url": row.url,
            "final_url": row.url,
            "status": "error",
            "fetch_status": str(getattr(result, "status", "error")),
            "status_code": int(getattr(result, "http_status", 0) or 0),
            "fetched_at": str(getattr(result, "fetched_at", now_iso())),
            "html_path": "",
            "content_type": "text/markdown",
            "provider": str(getattr(result, "provider", "")),
            "quality_score": float(getattr(result, "quality_score", 0.0) or 0.0),
            "requires_auth": bool(getattr(result, "requires_auth", False)),
            "error": str(getattr(result, "error_reason", "")),
            "title": str(getattr(result, "title", "")),
            "content_text": str(getattr(result, "content", "")),
            "html_sha1": "",
        }
        if payload["fetch_status"] == "ok" and payload["content_text"]:
            payload["status"] = "success"
            payload["error"] = ""
            payload["html_sha1"] = sha1_text(payload["content_text"])
        return payload

    return await asyncio.to_thread(run_sync)



async def fetch_all_with_skill(
    rows: list[SourceRow],
    *,
    skill_module: Any,
    providers: list[str],
    timeout: int,
    max_chars: int,
    concurrency: int,
) -> list[dict]:
    semaphore = asyncio.Semaphore(concurrency)

    async def runner(row: SourceRow) -> dict:
        async with semaphore:
            return await fetch_source_with_skill(
                row,
                skill_module=skill_module,
                providers=providers,
                timeout=timeout,
                max_chars=max_chars,
            )

    tasks = [runner(row) for row in rows]
    return await asyncio.gather(*tasks)


