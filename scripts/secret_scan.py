#!/usr/bin/env python3
"""
Scan repository text files for likely plaintext secrets.

This script is designed for two scenarios:
1) Local pre-commit checks (`--staged`) to block accidental leaks.
2) CI checks on full repo snapshots.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


IGNORE_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "artifacts",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}

IGNORE_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".webp",
    ".ico",
    ".zip",
    ".7z",
    ".rar",
    ".pdf",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".woff",
    ".woff2",
}

# High-confidence patterns. We intentionally keep these strict to reduce noise.
PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("dify_app_key", re.compile(r"\bapp-[A-Za-z0-9]{20,}\b")),
    ("openai_style_key", re.compile(r"\bsk-[A-Za-z0-9_\-=/+]{20,}\b")),
    (
        "generic_secret_assignment",
        re.compile(
            r"(?i)\b(api[_ -]?key|token|secret|password|passwd)\b"
            r"\s*[:=]\s*[`\"'][A-Za-z0-9_\-=/+]{12,}[`\"']"
        ),
    ),
]

ALLOW_SNIPPET_MARKERS = (
    "redacted",
    "placeholder",
    "example",
    "sample",
    "your_",
    "<redacted",
    "xxxxxx",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan repo for likely plaintext secrets.")
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root path. Default: current directory.",
    )
    parser.add_argument(
        "--staged",
        action="store_true",
        help="Only scan staged files from git index.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Print only findings summary.",
    )
    parser.add_argument(
        "--paths",
        nargs="*",
        default=None,
        help="Optional explicit paths to scan (relative to repo root or absolute).",
    )
    return parser.parse_args()


def iter_repo_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for root, dirnames, filenames in os.walk(repo_root, topdown=True):
        dirnames[:] = [name for name in dirnames if name not in IGNORE_DIRS]
        root_path = Path(root)
        for filename in filenames:
            path = root_path / filename
            if path.suffix.lower() in IGNORE_SUFFIXES:
                continue
            files.append(path)
    return files


def git_staged_files(repo_root: Path) -> list[Path]:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return []

    files: list[Path] = []
    for raw in completed.stdout.splitlines():
        rel = raw.strip()
        if not rel:
            continue
        path = (repo_root / rel).resolve()
        if not path.exists() or not path.is_file():
            continue
        if any(part in IGNORE_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in IGNORE_SUFFIXES:
            continue
        files.append(path)
    return files


def normalize_paths(repo_root: Path, paths: list[str]) -> list[Path]:
    resolved: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if not path.is_absolute():
            path = (repo_root / path).resolve()
        if not path.exists() or not path.is_file():
            continue
        if path.suffix.lower() in IGNORE_SUFFIXES:
            continue
        resolved.append(path)
    return resolved


def read_text_lines(path: Path) -> list[str] | None:
    encodings = ("utf-8", "utf-8-sig", "gbk")
    for encoding in encodings:
        try:
            text = path.read_text(encoding=encoding)
            return text.splitlines()
        except UnicodeDecodeError:
            continue
        except OSError:
            return None
    return None


def should_skip_line(line: str) -> bool:
    lowered = line.lower()
    return any(marker in lowered for marker in ALLOW_SNIPPET_MARKERS)


def scan_file(path: Path, repo_root: Path) -> list[tuple[str, int, str, str]]:
    lines = read_text_lines(path)
    if lines is None:
        return []

    findings: list[tuple[str, int, str, str]] = []
    rel_path = str(path.relative_to(repo_root)).replace("\\", "/")

    for lineno, line in enumerate(lines, start=1):
        if should_skip_line(line):
            continue
        for name, pattern in PATTERNS:
            if pattern.search(line):
                snippet = line.strip()
                if len(snippet) > 200:
                    snippet = snippet[:200] + "..."
                findings.append((rel_path, lineno, name, snippet))
    return findings


def pick_files(args: argparse.Namespace, repo_root: Path) -> list[Path]:
    if args.paths:
        return normalize_paths(repo_root, args.paths)
    if args.staged:
        return git_staged_files(repo_root)
    return iter_repo_files(repo_root)


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    files = pick_files(args, repo_root)

    findings: list[tuple[str, int, str, str]] = []
    for path in files:
        findings.extend(scan_file(path, repo_root))

    if findings:
        if not args.quiet:
            print("Potential secrets detected:")
            for rel_path, lineno, rule, snippet in findings:
                print(f"- {rel_path}:{lineno} [{rule}] {snippet}")
        else:
            print(f"Potential secrets detected: {len(findings)} hit(s).")
        return 1

    if not args.quiet:
        print(f"Secret scan passed. Scanned files: {len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
