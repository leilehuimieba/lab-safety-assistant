#!/usr/bin/env python3
"""
Web page content extraction utilities.

HTML parsing, noise removal, title/description/date extraction, and text normalization.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

try:
    from bs4 import BeautifulSoup
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Missing dependencies. Run: pip install -r scripts/requirements-web-ingest.txt"
    ) from exc

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



def clean_web_text(text: str) -> str:
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



def extract_publish_date_from_text(text: str) -> str:
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
        text = clean_web_text(node.get_text("\n", strip=True))
        if not text:
            return 0
        link_text = clean_web_text(" ".join(a.get_text(" ", strip=True) for a in node.find_all("a")))
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
    main_text = clean_web_text(best_node.get_text("\n", strip=True))
    title = extract_title(soup, fallback="")
    description = extract_description(soup, fallback_text=main_text)
    return title, description, main_text


