#!/usr/bin/env python3
"""
Multi-channel webpage content fetcher:
- jina reader
- scrapling (optional dependency)
- direct html fallback
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

import requests

try:
    from bs4 import BeautifulSoup
    from bs4 import FeatureNotFound
except ImportError:  # pragma: no cover
    BeautifulSoup = None  # type: ignore[assignment]
    FeatureNotFound = Exception  # type: ignore[assignment]

try:
    import html2text  # type: ignore
except ImportError:  # pragma: no cover
    html2text = None  # type: ignore[assignment]


DEFAULT_TIMEOUT = 20
DEFAULT_MAX_CHARS = 30000
DEFAULT_PROVIDERS = ["jina", "scrapling", "direct"]
SCRAPLING_FIRST_DOMAINS = ("weixin.qq.com", "mp.weixin.qq.com", "xiaohongshu.com")

BLOCK_HINTS = [
    "登录",
    "sign in",
    "forbidden",
    "访问受限",
    "需要登录",
    "验证",
    "captcha",
    "权限不足",
]


@dataclass
class FetchResult:
    url: str
    status: str
    provider: str
    title: str
    content: str
    quality_score: float
    requires_auth: bool
    http_status: int | None
    error_reason: str
    fetched_at: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch webpage正文 with provider fallback.")
    parser.add_argument("--url", action="append", default=[], help="Target URL (repeatable).")
    parser.add_argument("--url-file", default="", help="CSV file containing URLs.")
    parser.add_argument("--url-column", default="url", help="URL column name in CSV file.")
    parser.add_argument(
        "--providers",
        default=",".join(DEFAULT_PROVIDERS),
        help="Provider order, comma-separated: jina,scrapling,direct",
    )
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="HTTP timeout (seconds).")
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS, help="Content char limit.")
    parser.add_argument("--out-json", default="", help="Write result list to JSON file.")
    parser.add_argument("--pretty", action="store_true", help="Pretty print JSON output.")
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def normalize_url(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        return ""
    if not re.match(r"^https?://", value, re.IGNORECASE):
        return f"https://{value}"
    return value


def clip_text(text: str, max_chars: int) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars].rstrip() + " ..."


def detect_auth_wall(text: str) -> bool:
    lowered = (text or "").lower()
    return any(token in lowered for token in BLOCK_HINTS)


def quality_score(text: str) -> float:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if not cleaned:
        return 0.0
    length_score = min(len(cleaned) / 3500.0, 1.0)
    sentence_count = len(re.findall(r"[。！？.!?]", cleaned))
    sentence_score = min(sentence_count / 35.0, 1.0)
    alpha_count = len(re.findall(r"[A-Za-z\u4e00-\u9fff]", cleaned))
    density = alpha_count / max(len(cleaned), 1)
    density_score = min(max(density, 0.0), 1.0)
    score = 0.5 * length_score + 0.3 * sentence_score + 0.2 * density_score
    return round(min(max(score, 0.0), 1.0), 4)


def sanitize_broken_entities(html: str) -> str:
    if not html:
        return ""

    # Keep valid numeric entities like &#123; / &#x1F44D;, drop malformed ones.
    pattern = re.compile(r"&#([^;\s]{1,40});?")

    def repl(match: re.Match[str]) -> str:
        token = (match.group(1) or "").strip()
        if re.fullmatch(r"[0-9]{1,7}", token):
            return match.group(0)
        if re.fullmatch(r"[xX][0-9A-Fa-f]{1,6}", token):
            return match.group(0)
        return " "

    return pattern.sub(repl, html)


def html_to_text(html: str) -> tuple[str, str]:
    title = ""
    if not html:
        return title, ""

    if BeautifulSoup is None:  # pragma: no cover
        plain = re.sub(r"<[^>]+>", " ", html)
        plain = re.sub(r"\s+", " ", plain).strip()
        return title, plain

    soup = None
    safe_html = sanitize_broken_entities(html)
    for parser in ("html.parser", "lxml", "html5lib"):
        try:
            soup = BeautifulSoup(safe_html, parser)
            break
        except FeatureNotFound:
            continue
        except Exception:
            continue
    if soup is None:
        plain = re.sub(r"<[^>]+>", " ", safe_html)
        plain = re.sub(r"\s+", " ", plain).strip()
        return title, plain

    title = (soup.title.text or "").strip() if soup.title else ""

    for tag in soup.find_all(["script", "style", "noscript", "footer", "header", "nav", "aside", "form"]):
        tag.decompose()

    container = soup.find("article") or soup.find("main") or soup.body or soup
    if html2text is not None:
        converter = html2text.HTML2Text()
        converter.ignore_links = False
        converter.ignore_images = True
        converter.body_width = 0
        try:
            markdown_text = converter.handle(str(container))
        except Exception:
            markdown_text = container.get_text(" ", strip=True)
        markdown_text = re.sub(r"\n{3,}", "\n\n", markdown_text).strip()
        return title, markdown_text

    blocks = []
    for node in container.find_all(["h1", "h2", "h3", "p", "li", "blockquote"]):
        text = node.get_text(" ", strip=True)
        if text:
            blocks.append(text)
    return title, "\n".join(blocks).strip()


def fetch_jina(url: str, timeout: int, max_chars: int) -> FetchResult:
    jina_url = f"https://r.jina.ai/http://{url}" if url.startswith("http://") else f"https://r.jina.ai/{url}"
    try:
        resp = requests.get(jina_url, timeout=timeout)
    except requests.RequestException as exc:
        return FetchResult(
            url=url,
            status="error",
            provider="jina",
            title="",
            content="",
            quality_score=0.0,
            requires_auth=False,
            http_status=None,
            error_reason=f"jina_request_error:{type(exc).__name__}",
            fetched_at=utc_now(),
        )
    text = (resp.text or "").strip()
    requires_auth = detect_auth_wall(text)
    status = "ok" if resp.status_code == 200 and text else "error"
    if requires_auth and status == "ok":
        status = "blocked"
    return FetchResult(
        url=url,
        status=status,
        provider="jina",
        title=(text.splitlines()[0].strip("# ").strip() if text else ""),
        content=clip_text(text, max_chars=max_chars),
        quality_score=quality_score(text),
        requires_auth=requires_auth,
        http_status=resp.status_code,
        error_reason="" if status == "ok" else f"jina_status_{resp.status_code}",
        fetched_at=utc_now(),
    )


def fetch_scrapling(url: str, timeout: int, max_chars: int) -> FetchResult:
    try:
        import scrapling  # type: ignore
    except Exception:
        return FetchResult(
            url=url,
            status="error",
            provider="scrapling",
            title="",
            content="",
            quality_score=0.0,
            requires_auth=False,
            http_status=None,
            error_reason="scrapling_not_installed",
            fetched_at=utc_now(),
        )

    html = ""
    error_reason = "scrapling_runtime_error"
    try:
        fetcher = getattr(scrapling, "Fetcher", None)
        if fetcher is not None:
            client = fetcher(timeout=timeout)
            response = client.get(url)
            html = str(getattr(response, "text", "") or getattr(response, "content", "") or "")
        else:
            # Some versions expose helper methods instead of Fetcher.
            if hasattr(scrapling, "fetch"):
                response = scrapling.fetch(url, timeout=timeout)  # type: ignore[attr-defined]
                html = str(getattr(response, "text", "") or response or "")
            else:
                error_reason = "scrapling_api_not_supported"
    except Exception as exc:  # pragma: no cover
        error_reason = f"scrapling_exception:{type(exc).__name__}"

    title, text = html_to_text(html)
    requires_auth = detect_auth_wall(text)
    status = "ok" if text else "error"
    if requires_auth and status == "ok":
        status = "blocked"
    return FetchResult(
        url=url,
        status=status,
        provider="scrapling",
        title=title,
        content=clip_text(text, max_chars=max_chars),
        quality_score=quality_score(text),
        requires_auth=requires_auth,
        http_status=None,
        error_reason="" if status == "ok" else error_reason,
        fetched_at=utc_now(),
    )


def fetch_direct(url: str, timeout: int, max_chars: int) -> FetchResult:
    try:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0 (compatible; WebContentFetcher/1.0)"})
    except requests.RequestException as exc:
        return FetchResult(
            url=url,
            status="error",
            provider="direct",
            title="",
            content="",
            quality_score=0.0,
            requires_auth=False,
            http_status=None,
            error_reason=f"direct_request_error:{type(exc).__name__}",
            fetched_at=utc_now(),
        )

    title, text = html_to_text(resp.text or "")
    requires_auth = detect_auth_wall(text)
    status = "ok" if resp.status_code == 200 and text else "error"
    if requires_auth and status == "ok":
        status = "blocked"
    return FetchResult(
        url=url,
        status=status,
        provider="direct",
        title=title,
        content=clip_text(text, max_chars=max_chars),
        quality_score=quality_score(text),
        requires_auth=requires_auth,
        http_status=resp.status_code,
        error_reason="" if status == "ok" else f"direct_status_{resp.status_code}",
        fetched_at=utc_now(),
    )


def load_urls_from_file(path: Path, column: str) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [normalize_url(row.get(column, "")) for row in reader if normalize_url(row.get(column, ""))]


def route_providers(url: str, providers: list[str]) -> list[str]:
    host = (urlparse(url).hostname or "").lower()
    if any(domain in host for domain in SCRAPLING_FIRST_DOMAINS) and "scrapling" in providers:
        ordered = ["scrapling"] + [p for p in providers if p != "scrapling"]
        return ordered
    return providers


def fetch_with_fallback(url: str, providers: list[str], timeout: int, max_chars: int) -> FetchResult:
    handlers: dict[str, Callable[[str, int, int], FetchResult]] = {
        "jina": fetch_jina,
        "scrapling": fetch_scrapling,
        "direct": fetch_direct,
    }
    ordered = route_providers(url, providers)
    last = FetchResult(
        url=url,
        status="error",
        provider="none",
        title="",
        content="",
        quality_score=0.0,
        requires_auth=False,
        http_status=None,
        error_reason="no_provider_attempted",
        fetched_at=utc_now(),
    )
    for provider in ordered:
        handler = handlers.get(provider)
        if handler is None:
            continue
        result = handler(url, timeout, max_chars)
        if result.status == "ok":
            return result
        last = result
        if result.status == "blocked":
            return result
    return last


def main() -> int:
    args = parse_args()
    providers = [item.strip().lower() for item in args.providers.split(",") if item.strip()]
    providers = [p for p in providers if p in {"jina", "scrapling", "direct"}]
    if not providers:
        raise SystemExit("No valid providers. Use jina,scrapling,direct.")

    urls = [normalize_url(item) for item in args.url if normalize_url(item)]
    if args.url_file:
        file_urls = load_urls_from_file(Path(args.url_file).resolve(), args.url_column)
        urls.extend(file_urls)
    # unique and preserve order
    seen = set()
    ordered_urls = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            ordered_urls.append(url)
    if not ordered_urls:
        raise SystemExit("No input URLs found.")

    results = [
        asdict(fetch_with_fallback(url, providers=providers, timeout=args.timeout, max_chars=args.max_chars))
        for url in ordered_urls
    ]
    payload = {"count": len(results), "results": results}
    if args.out_json:
        out_path = Path(args.out_json)
        if not out_path.is_absolute():
            out_path = Path.cwd() / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    output = json.dumps(payload, ensure_ascii=False)
    # Windows 默认控制台编码可能是 gbk，遇到特殊字符时直接 print 会抛 UnicodeEncodeError。
    if args.pretty:
        output = json.dumps(payload, ensure_ascii=False, indent=2)
    try:
        print(output)
    except UnicodeEncodeError:  # pragma: no cover
        sys.stdout.buffer.write(output.encode("utf-8", errors="replace"))
        sys.stdout.buffer.write(b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
