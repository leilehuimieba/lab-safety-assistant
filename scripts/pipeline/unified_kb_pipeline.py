#!/usr/bin/env python3
"""
Run document and web ingestion, then merge both outputs into one unified KB CSV.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


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


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_csv_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [{field: row.get(field, "") for field in KB_FIELDNAMES} for row in reader]


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=KB_FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in KB_FIELDNAMES})


def merge_rows(row_groups: list[list[dict]]) -> list[dict]:
    merged: list[dict] = []
    seen_ids: set[str] = set()
    for rows in row_groups:
        for row in rows:
            row_id = row.get("id", "")
            if not row_id or row_id in seen_ids:
                continue
            merged.append({field: row.get(field, "") for field in KB_FIELDNAMES})
            seen_ids.add(row_id)
    return merged


def merge_into_csv(path: Path, new_rows: list[dict]) -> int:
    existing_rows = read_csv_rows(path)
    existing_ids = {row["id"] for row in existing_rows if row.get("id")}
    appended = 0
    for row in new_rows:
        if row["id"] in existing_ids:
            continue
        existing_rows.append({field: row.get(field, "") for field in KB_FIELDNAMES})
        existing_ids.add(row["id"])
        appended += 1
    write_csv(path, existing_rows)
    return appended


def run_command(command: list[str], cwd: Path) -> dict:
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def build_document_command(args: argparse.Namespace, output_dir: Path, repo_root: Path) -> list[str]:
    command = [
        sys.executable,
        str(repo_root / "scripts" / "document_ingest_pipeline.py"),
        "--input-root",
        args.document_input_root,
        "--output-dir",
        str(output_dir),
        "--max-chars",
        str(args.document_max_chars),
        "--overlap",
        str(args.document_overlap),
        "--pdf-ocr-mode",
        args.pdf_ocr_mode,
    ]
    manifest = Path(args.document_manifest)
    if manifest.exists():
        command.extend(["--manifest", args.document_manifest])
    pdf_special_rules = Path(args.document_pdf_special_rules)
    if pdf_special_rules.exists():
        command.extend(["--pdf-special-rules", args.document_pdf_special_rules])
    if args.document_only_manifest:
        command.append("--only-manifest")
    if args.extract_zips:
        command.append("--extract-zips")
    if args.document_limit > 0:
        command.extend(["--limit", str(args.document_limit)])
    return command


def build_web_command(args: argparse.Namespace, output_dir: Path, repo_root: Path) -> list[str]:
    command = [
        sys.executable,
        str(repo_root / "scripts" / "web_ingest_pipeline.py"),
        "--manifest",
        args.web_manifest,
        "--output-dir",
        str(output_dir),
        "--concurrency",
        str(args.web_concurrency),
        "--max-chars",
        str(args.web_max_chars),
        "--overlap",
        str(args.web_overlap),
        "--fetcher-mode",
        args.web_fetcher_mode,
        "--skill-providers",
        args.web_skill_providers,
        "--fetch-timeout",
        str(args.web_fetch_timeout),
        "--fetch-max-chars",
        str(args.web_fetch_max_chars),
    ]
    if args.web_skill_script:
        command.extend(["--skill-script", args.web_skill_script])
    return command


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run document and web ingestion, then merge into one KB CSV."
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts\\unified_ingest",
        help="Directory for sub-pipeline outputs and the merged CSV.",
    )
    parser.add_argument(
        "--document-input-root",
        default="..\\data",
        help="Root directory for PDF/Word/PPT ingestion.",
    )
    parser.add_argument(
        "--document-manifest",
        default="data_sources\\document_manifest.csv",
        help="Optional document metadata manifest.",
    )
    parser.add_argument(
        "--document-only-manifest",
        action="store_true",
        help="Only ingest documents that are explicitly listed in the document manifest.",
    )
    parser.add_argument(
        "--document-pdf-special-rules",
        default="data_sources\\pdf_special_rules.csv",
        help="Optional per-file PDF override CSV for document ingestion.",
    )
    parser.add_argument(
        "--extract-zips",
        action="store_true",
        help="Extract zip archives before document ingestion.",
    )
    parser.add_argument(
        "--document-limit",
        type=int,
        default=0,
        help="Optional cap on document files for testing.",
    )
    parser.add_argument(
        "--document-max-chars",
        type=int,
        default=1400,
        help="Maximum characters per document chunk.",
    )
    parser.add_argument(
        "--document-overlap",
        type=int,
        default=120,
        help="Character overlap between document chunks.",
    )
    parser.add_argument(
        "--pdf-ocr-mode",
        choices=["auto", "off", "always"],
        default="auto",
        help="PDF OCR fallback mode for document ingestion.",
    )
    parser.add_argument(
        "--web-manifest",
        default="data_sources\\web_seed_urls.csv",
        help="Web source manifest for web ingestion.",
    )
    parser.add_argument(
        "--web-concurrency",
        type=int,
        default=3,
        help="Concurrent web fetch count.",
    )
    parser.add_argument(
        "--web-max-chars",
        type=int,
        default=1200,
        help="Maximum characters per web chunk.",
    )
    parser.add_argument(
        "--web-overlap",
        type=int,
        default=120,
        help="Character overlap between web chunks.",
    )
    parser.add_argument(
        "--web-fetcher-mode",
        choices=["auto", "legacy", "skill"],
        default="auto",
        help="Web fetch mode passed to web_ingest_pipeline (default: auto, 优先skill).",
    )
    parser.add_argument(
        "--web-skill-script",
        default="",
        help="Optional path to fetch_web_content.py passed to web_ingest_pipeline.",
    )
    parser.add_argument(
        "--web-skill-providers",
        default="jina,scrapling,direct",
        help="Provider order for skill mode web fetch.",
    )
    parser.add_argument(
        "--web-fetch-timeout",
        type=int,
        default=20,
        help="Fetch timeout passed to web_ingest_pipeline skill fetch.",
    )
    parser.add_argument(
        "--web-fetch-max-chars",
        type=int,
        default=30000,
        help="Max chars for skill fetch result before web chunking.",
    )
    parser.add_argument(
        "--skip-documents",
        action="store_true",
        help="Skip PDF/Word/PPT ingestion.",
    )
    parser.add_argument(
        "--skip-web",
        action="store_true",
        help="Skip web ingestion.",
    )
    parser.add_argument(
        "--merge-into",
        default="",
        help="Optional path to append unique merged rows into an existing CSV.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    output_dir = Path(args.output_dir)
    documents_dir = output_dir / "documents"
    web_dir = output_dir / "web"
    output_dir.mkdir(parents=True, exist_ok=True)

    run_logs: dict[str, dict] = {}
    row_groups: list[list[dict]] = []

    if not args.skip_documents:
        documents_dir.mkdir(parents=True, exist_ok=True)
        doc_command = build_document_command(args, documents_dir, repo_root)
        doc_run = run_command(doc_command, cwd=repo_root)
        run_logs["documents"] = doc_run
        if doc_run["returncode"] != 0:
            raise SystemExit(
                "Document ingestion failed.\n"
                f"STDOUT:\n{doc_run['stdout']}\nSTDERR:\n{doc_run['stderr']}"
            )
        row_groups.append(read_csv_rows(documents_dir / "knowledge_base_documents.csv"))

    if not args.skip_web:
        manifest = Path(args.web_manifest)
        if manifest.exists():
            web_dir.mkdir(parents=True, exist_ok=True)
            web_command = build_web_command(args, web_dir, repo_root)
            web_run = run_command(web_command, cwd=repo_root)
            run_logs["web"] = web_run
            if web_run["returncode"] != 0:
                raise SystemExit(
                    "Web ingestion failed.\n"
                    f"STDOUT:\n{web_run['stdout']}\nSTDERR:\n{web_run['stderr']}"
                )
            row_groups.append(read_csv_rows(web_dir / "knowledge_base_web.csv"))
        else:
            run_logs["web"] = {
                "command": [],
                "returncode": 0,
                "stdout": "",
                "stderr": f"Skipped because manifest was not found: {manifest}",
            }

    merged_rows = merge_rows(row_groups)
    merged_csv = output_dir / "knowledge_base_unified.csv"
    write_csv(merged_csv, merged_rows)

    merged_count = 0
    if args.merge_into:
        merged_count = merge_into_csv(Path(args.merge_into), merged_rows)

    report = {
        "generated_at": now_iso(),
        "documents_rows": len(row_groups[0]) if row_groups and not args.skip_documents else 0,
        "web_rows": len(row_groups[-1]) if row_groups and not args.skip_web and Path(args.web_manifest).exists() else 0,
        "merged_rows": len(merged_rows),
        "merge_into_appended": merged_count,
        "runs": {
            key: {
                "returncode": value["returncode"],
                "command": value["command"],
                "stdout_tail": value["stdout"][-2000:],
                "stderr_tail": value["stderr"][-2000:],
            }
            for key, value in run_logs.items()
        },
        "web_fetcher_mode": args.web_fetcher_mode if not args.skip_web else "skipped",
    }
    (output_dir / "run_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Merged rows: {len(merged_rows)}")
    print(f"Unified CSV: {merged_csv.resolve()}")
    if args.merge_into:
        print(f"Merged into existing CSV: {Path(args.merge_into).resolve()} ({merged_count} new rows)")


if __name__ == "__main__":
    main()
