#!/usr/bin/env python3
"""
Wrapper: run repository web_ingest_pipeline with skill fetch mode enabled.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run web_ingest_pipeline via web-content-fetcher skill.")
    parser.add_argument("--repo-root", default=".", help="Repository root path.")
    parser.add_argument("--manifest", default="data_sources/web_seed_urls.csv", help="Web seed manifest.")
    parser.add_argument("--output-dir", default="artifacts/web_ingest_skill", help="Output directory.")
    parser.add_argument("--concurrency", type=int, default=3, help="Concurrent fetch count.")
    parser.add_argument("--max-chars", type=int, default=1200, help="KB chunk max chars.")
    parser.add_argument("--overlap", type=int, default=120, help="KB chunk overlap.")
    parser.add_argument("--merge-into", default="", help="Optional merge target CSV.")
    parser.add_argument("--providers", default="jina,scrapling,direct", help="Skill provider order.")
    parser.add_argument("--fetch-timeout", type=int, default=20, help="Fetch timeout seconds.")
    parser.add_argument("--fetch-max-chars", type=int, default=30000, help="Skill content max chars.")
    return parser.parse_args()


def resolve(path: str, base: Path) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = base / p
    return p.resolve()


def main() -> int:
    args = parse_args()
    repo_root = resolve(args.repo_root, Path.cwd())
    pipeline = repo_root / "scripts" / "web_ingest_pipeline.py"
    skill_script = repo_root / "skills" / "web-content-fetcher" / "scripts" / "fetch_web_content.py"
    if not pipeline.exists():
        raise SystemExit(f"Pipeline not found: {pipeline}")
    if not skill_script.exists():
        raise SystemExit(f"Skill script not found: {skill_script}")

    cmd = [
        sys.executable,
        str(pipeline),
        "--manifest",
        str(resolve(args.manifest, repo_root)),
        "--output-dir",
        str(resolve(args.output_dir, repo_root)),
        "--concurrency",
        str(args.concurrency),
        "--max-chars",
        str(args.max_chars),
        "--overlap",
        str(args.overlap),
        "--fetcher-mode",
        "skill",
        "--skill-script",
        str(skill_script),
        "--skill-providers",
        args.providers,
        "--fetch-timeout",
        str(args.fetch_timeout),
        "--fetch-max-chars",
        str(args.fetch_max_chars),
    ]
    if args.merge_into:
        cmd.extend(["--merge-into", str(resolve(args.merge_into, repo_root))])

    completed = subprocess.run(cmd, cwd=str(repo_root), check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())

