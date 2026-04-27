#!/usr/bin/env python3
"""
Wrapper: run repository unified_kb_pipeline with web skill mode enabled.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run unified_kb_pipeline via web-content-fetcher skill.")
    parser.add_argument("--repo-root", default=".", help="Repository root path.")
    parser.add_argument("--output-dir", default="artifacts/unified_ingest_skill", help="Output directory.")
    parser.add_argument("--document-input-root", default="..\\data", help="Document root directory.")
    parser.add_argument("--document-manifest", default="data_sources\\document_manifest.csv", help="Document manifest.")
    parser.add_argument("--document-pdf-special-rules", default="data_sources\\pdf_special_rules.csv", help="PDF special rules.")
    parser.add_argument("--web-manifest", default="data_sources\\web_seed_urls.csv", help="Web manifest.")
    parser.add_argument("--web-skill-providers", default="jina,scrapling,direct", help="Skill provider order.")
    parser.add_argument("--web-fetch-timeout", type=int, default=20, help="Web fetch timeout.")
    parser.add_argument("--web-fetch-max-chars", type=int, default=30000, help="Skill fetch max chars.")
    parser.add_argument("--pdf-ocr-mode", choices=["auto", "off", "always"], default="auto", help="PDF OCR mode.")
    parser.add_argument("--skip-documents", action="store_true", help="Skip document ingestion.")
    parser.add_argument("--skip-web", action="store_true", help="Skip web ingestion.")
    parser.add_argument("--merge-into", default="", help="Optional merge target CSV.")
    return parser.parse_args()


def resolve(path: str, base: Path) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = base / p
    return p.resolve()


def main() -> int:
    args = parse_args()
    repo_root = resolve(args.repo_root, Path.cwd())
    pipeline = repo_root / "scripts" / "unified_kb_pipeline.py"
    skill_script = repo_root / "skills" / "web-content-fetcher" / "scripts" / "fetch_web_content.py"
    if not pipeline.exists():
        raise SystemExit(f"Pipeline not found: {pipeline}")
    if not skill_script.exists():
        raise SystemExit(f"Skill script not found: {skill_script}")

    cmd = [
        sys.executable,
        str(pipeline),
        "--output-dir",
        str(resolve(args.output_dir, repo_root)),
        "--document-input-root",
        str(resolve(args.document_input_root, repo_root)),
        "--document-manifest",
        str(resolve(args.document_manifest, repo_root)),
        "--document-pdf-special-rules",
        str(resolve(args.document_pdf_special_rules, repo_root)),
        "--pdf-ocr-mode",
        args.pdf_ocr_mode,
        "--web-manifest",
        str(resolve(args.web_manifest, repo_root)),
        "--web-fetcher-mode",
        "skill",
        "--web-skill-script",
        str(skill_script),
        "--web-skill-providers",
        args.web_skill_providers,
        "--web-fetch-timeout",
        str(args.web_fetch_timeout),
        "--web-fetch-max-chars",
        str(args.web_fetch_max_chars),
    ]
    if args.skip_documents:
        cmd.append("--skip-documents")
    if args.skip_web:
        cmd.append("--skip-web")
    if args.merge_into:
        cmd.extend(["--merge-into", str(resolve(args.merge_into, repo_root))])

    completed = subprocess.run(cmd, cwd=str(repo_root), check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())

