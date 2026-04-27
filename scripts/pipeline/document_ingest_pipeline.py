#!/usr/bin/env python3
"""
Document ingestion pipeline: discover, extract, chunk, and export to knowledge-base CSV.
"""

from __future__ import annotations
from libs.common_io import now_iso

import argparse
import csv
import fnmatch
import json
import re
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path

try:
    from docx import Document as DocxDocument
    from pptx import Presentation
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Missing dependencies. Run: pip install -r scripts/requirements-document-ingest.txt"
    ) from exc

from libs.ingest_io import (
    clean_document_text,
    normalize_rel_path,
    sha1_text,
    split_into_chunks,
    write_jsonl,
    write_csv,
    merge_into_csv,
)
from pdf_extractor import extract_pdf, load_pdf_special_rules, match_pdf_special_rule

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".doc", ".ppt"}
DIRECT_EXTENSIONS = {".pdf", ".docx", ".pptx"}
ZIP_EXTENSION = ".zip"
CONVERSION_TARGETS = {".doc": ".docx", ".ppt": ".pptx"}

LAB_KEYWORDS = {
    "化学": "化学",
    "危化": "化学",
    "试剂": "化学",
    "酸": "化学",
    "碱": "化学",
    "电气": "电气",
    "高压": "电气",
    "触电": "电气",
    "生物": "生物",
    "菌": "生物",
    "消防": "通用",
    "火灾": "通用",
    "实验室": "通用",
}

HAZARD_KEYWORDS = {
    "高压": "高压",
    "易燃": "易燃",
    "腐蚀": "腐蚀性",
    "辐射": "辐射",
    "X射线": "辐射",
    "气瓶": "高压气体",
    "火灾": "火灾",
    "触电": "触电",
}

def load_manifest(path: Path | None) -> dict[str, dict]:
    if not path or not path.exists():
        return {}
    result: dict[str, dict] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            key = normalize_rel_path(row.get("path") or "")
            if key:
                result[key] = row
    return result

def infer_lab_type(text: str) -> str:
    for keyword, lab_type in LAB_KEYWORDS.items():
        if keyword in text:
            return lab_type
    return "通用"

def infer_hazards(text: str) -> str:
    hits: list[str] = []
    for keyword, hazard in HAZARD_KEYWORDS.items():
        if keyword in text and hazard not in hits:
            hits.append(hazard)
    return ";".join(hits) if hits else "综合安全"

def infer_subcategory(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "PDF资料"
    if suffix in {".docx", ".doc"}:
        return "Word资料"
    if suffix in {".pptx", ".ppt"}:
        return "PPT资料"
    return "文档资料"

def build_metadata(file_path: Path, input_root: Path, manifest: dict[str, dict]) -> dict:
    try:
        rel_path = str(file_path.relative_to(input_root)).replace("/", "\\")
    except ValueError:
        rel_path = file_path.name
    manifest_row = manifest.get(rel_path.lower(), {})
    filename_text = file_path.stem
    title = (manifest_row.get("source_title") or filename_text).strip()
    question_hint = (manifest_row.get("question_hint") or title).strip()
    source_org = (manifest_row.get("source_org") or "").strip()
    category = (manifest_row.get("category") or "通用").strip()
    subcategory = (manifest_row.get("subcategory") or infer_subcategory(file_path)).strip()
    lab_type = (manifest_row.get("lab_type") or infer_lab_type(title + rel_path)).strip()
    risk_level = (manifest_row.get("risk_level") or "3").strip()
    hazard_types = (manifest_row.get("hazard_types") or infer_hazards(title + rel_path)).strip()
    tags = (manifest_row.get("tags") or f"{file_path.suffix.lower().lstrip('.')};{file_path.parent.name}").strip()
    language = (manifest_row.get("language") or "zh-CN").strip()
    reviewer = (manifest_row.get("reviewer") or "").strip()
    return {
        "path": rel_path,
        "source_title": title,
        "source_org": source_org,
        "category": category,
        "subcategory": subcategory,
        "lab_type": lab_type,
        "risk_level": risk_level,
        "hazard_types": hazard_types,
        "tags": tags,
        "language": language,
        "question_hint": question_hint,
        "reviewer": reviewer,
    }
def extract_docx(path: Path) -> str:
    doc = DocxDocument(str(path))
    parts: list[str] = []
    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if text:
            parts.append(text)
    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    return "\n".join(parts)

def extract_pptx(path: Path) -> str:
    presentation = Presentation(str(path))
    parts: list[str] = []
    for index, slide in enumerate(presentation.slides, start=1):
        slide_lines: list[str] = [f"Slide {index}"]
        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text:
                text = shape.text.strip()
                if text:
                    slide_lines.append(text)
        if len(slide_lines) > 1:
            parts.append("\n".join(slide_lines))
    return "\n\n".join(parts)

def find_soffice() -> str | None:
    return shutil.which("soffice") or shutil.which("libreoffice")

def convert_legacy_file(path: Path, conversion_dir: Path) -> Path:
    target_suffix = CONVERSION_TARGETS[path.suffix.lower()]
    soffice = find_soffice()
    if not soffice:
        raise RuntimeError(f"Legacy file {path.name} requires LibreOffice/soffice for conversion")
    conversion_dir.mkdir(parents=True, exist_ok=True)
    command = [
        soffice,
        "--headless",
        "--convert-to",
        target_suffix.lstrip("."),
        "--outdir",
        str(conversion_dir),
        str(path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or f"Failed to convert {path.name}")
    converted = conversion_dir / f"{path.stem}{target_suffix}"
    if not converted.exists():
        raise RuntimeError(f"Converted file not found for {path.name}")
    return converted

def extract_text_from_file(
    path: Path,
    conversion_dir: Path,
    pdf_ocr_mode: str,
    pdf_special_rule: dict | None = None,
) -> tuple[str, str, Path, dict]:
    effective_path = path
    suffix = path.suffix.lower()
    if suffix in CONVERSION_TARGETS:
        effective_path = convert_legacy_file(path, conversion_dir)
        suffix = effective_path.suffix.lower()
    if suffix == ".pdf":
        text, extraction_meta = extract_pdf(
            effective_path,
            ocr_mode=pdf_ocr_mode,
            special_rule=pdf_special_rule,
        )
        return text, "PDF", effective_path, extraction_meta
    if suffix == ".docx":
        return extract_docx(effective_path), "Word", effective_path, {}
    if suffix == ".pptx":
        return extract_pptx(effective_path), "PPT", effective_path, {}
    raise RuntimeError(f"Unsupported file type: {path.suffix}")
def discover_input_files(input_root: Path, extract_zips: bool, extracted_dir: Path) -> list[Path]:
    files: list[Path] = []
    seen: set[str] = set()

    def add_candidate(path: Path) -> None:
        normalized = str(path.resolve()).lower()
        if normalized in seen:
            return
        seen.add(normalized)
        files.append(path)

    for path in input_root.rglob("*"):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix in SUPPORTED_EXTENSIONS:
            add_candidate(path)
        elif extract_zips and suffix == ZIP_EXTENSION:
            target_dir = extracted_dir / path.stem
            if not target_dir.exists():
                with zipfile.ZipFile(path, "r") as zip_ref:
                    zip_ref.extractall(target_dir)
            for extracted_file in target_dir.rglob("*"):
                if extracted_file.is_file() and extracted_file.suffix.lower() in SUPPORTED_EXTENSIONS:
                    add_candidate(extracted_file)
    return sorted(files)

def build_extract_record(
    file_path: Path,
    metadata: dict,
    text: str,
    source_type: str,
    effective_path: Path,
    extraction_meta: dict,
) -> dict:
    stat = effective_path.stat()
    normalized = clean_document_text(text)
    preview = normalized[:240]
    return {
        "source_id": metadata["path"],
        "file_path": str(file_path),
        "effective_path": str(effective_path),
        "source_title": metadata["source_title"],
        "source_org": metadata["source_org"],
        "category": metadata["category"],
        "subcategory": metadata["subcategory"],
        "lab_type": metadata["lab_type"],
        "risk_level": metadata["risk_level"],
        "hazard_types": metadata["hazard_types"],
        "tags": metadata["tags"],
        "language": metadata["language"],
        "question_hint": metadata["question_hint"],
        "reviewer": metadata["reviewer"],
        "source_type": source_type,
        "source_date": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d"),
        "content": normalized,
        "content_preview": preview,
        "content_sha1": sha1_text(normalized) if normalized else "",
        "char_count": len(normalized),
        "extraction_meta": extraction_meta,
    }

def build_kb_rows(documents: list[dict], max_chars: int, overlap: int) -> list[dict]:
    today = datetime.now().strftime("%Y-%m-%d")
    rows: list[dict] = []
    for document in documents:
        chunks = split_into_chunks(document["content"], max_chars=max_chars, overlap=overlap)
        question_hint = document["question_hint"] or document["source_title"]
        question = (
            question_hint
            if any(token in question_hint for token in ["哪些", "什么", "如何", "是否", "能否", "吗", "?", "？"])
            else f"{question_hint}有哪些要点？"
        )
        for idx, chunk in enumerate(chunks, start=1):
            rows.append(
                {
                    "id": f"DOC-{sha1_text(document['file_path'])[:8]}-{idx:03d}",
                    "title": document["source_title"] if idx == 1 else f"{document['source_title']}（片段{idx}）",
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
                    "legal_notes": "基于本地文档自动抽取，导入知识库前请人工复核。",
                    "references": f"{document['source_title']} | {document['file_path']}",
                    "source_type": document["source_type"],
                    "source_title": document["source_title"],
                    "source_org": document["source_org"],
                    "source_version": "",
                    "source_date": document["source_date"],
                    "source_url": document["file_path"],
                    "last_updated": today,
                    "reviewer": document["reviewer"],
                    "status": "draft",
                    "tags": document["tags"],
                    "language": document["language"],
                }
            )
    return rows
def write_report(path: Path, discovered: int, extracted: int, documents: int, rows: int, skipped: list[dict]) -> None:
    payload = {
        "generated_at": now_iso(),
        "discovered_files": discovered,
        "extracted_successfully": extracted,
        "clean_documents": documents,
        "knowledge_rows": rows,
        "skipped_files": skipped,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest PDF/Word/PPT files into knowledge-base CSV.")
    parser.add_argument(
        "--input-root",
        default="..\\data",
        help="Root directory that contains documents or extracted archives.",
    )
    parser.add_argument(
        "--manifest",
        default="data_sources\\document_manifest.csv",
        help="Optional CSV that overrides metadata per file. Use the template if you do not have one yet.",
    )
    parser.add_argument(
        "--only-manifest",
        action="store_true",
        help="Only ingest files that are explicitly listed in the manifest.",
    )
    parser.add_argument(
        "--pdf-special-rules",
        default="data_sources\\pdf_special_rules.csv",
        help="Optional CSV for per-file PDF extraction overrides such as force_ocr and body_start_page.",
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts\\document_ingest",
        help="Directory for extracted metadata, cleaned docs, and exported CSV.",
    )
    parser.add_argument(
        "--extract-zips",
        action="store_true",
        help="Extract zip archives found under input-root and scan their contents.",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=1400,
        help="Maximum characters per exported knowledge chunk.",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=120,
        help="Character overlap between chunks.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional cap on number of discovered files for testing.",
    )
    parser.add_argument(
        "--merge-into",
        default="",
        help="Optional path to append unique rows into an existing knowledge-base CSV.",
    )
    parser.add_argument(
        "--pdf-ocr-mode",
        choices=["auto", "off", "always"],
        default="auto",
        help="PDF fallback mode: auto uses PyMuPDF/pdfplumber/OCR only when needed.",
    )
    return parser.parse_args()

def main() -> None:
    args = parse_args()
    input_root = Path(args.input_root).resolve()
    output_dir = Path(args.output_dir)
    extracted_dir = output_dir / "extracted_archives"
    conversion_dir = output_dir / "converted_legacy"
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = Path(args.manifest)
    manifest = load_manifest(manifest_path if manifest_path.exists() else None)
    if args.only_manifest and not manifest:
        raise SystemExit("--only-manifest was set, but the manifest file was not found or was empty.")
    pdf_special_rules_path = Path(args.pdf_special_rules)
    pdf_special_rules = load_pdf_special_rules(
        pdf_special_rules_path if pdf_special_rules_path.exists() else None
    )

    discovered_files = discover_input_files(
        input_root=input_root,
        extract_zips=args.extract_zips,
        extracted_dir=extracted_dir,
    )
    if args.only_manifest:
        manifest_paths = set(manifest.keys())
        discovered_files = [
            file_path
            for file_path in discovered_files
            if normalize_rel_path(
                str(file_path.relative_to(input_root)) if file_path.is_relative_to(input_root) else file_path.name
            )
            in manifest_paths
        ]
    if args.limit and args.limit > 0:
        discovered_files = discovered_files[: args.limit]

    extract_results: list[dict] = []
    clean_documents: list[dict] = []
    skipped_files: list[dict] = []

    for file_path in discovered_files:
        metadata = build_metadata(file_path, input_root=input_root, manifest=manifest)
        pdf_special_rule = (
            match_pdf_special_rule(metadata["path"], pdf_special_rules)
            if file_path.suffix.lower() == ".pdf"
            else None
        )
        try:
            text, source_type, effective_path, extraction_meta = extract_text_from_file(
                file_path,
                conversion_dir,
                args.pdf_ocr_mode,
                pdf_special_rule=pdf_special_rule,
            )
            record = build_extract_record(
                file_path,
                metadata,
                text,
                source_type,
                effective_path,
                extraction_meta,
            )
            extract_results.append(record)
            if len(record["content"]) >= 80:
                clean_documents.append(record)
            else:
                skipped_files.append({"file_path": str(file_path), "reason": "content_too_short"})
        except Exception as exc:
            skipped_files.append({"file_path": str(file_path), "reason": str(exc)})

    write_jsonl(output_dir / "extract_results.jsonl", extract_results)
    write_jsonl(output_dir / "clean_documents.jsonl", clean_documents)

    kb_rows = build_kb_rows(clean_documents, max_chars=args.max_chars, overlap=args.overlap)
    write_csv(output_dir / "knowledge_base_documents.csv", kb_rows)

    if args.merge_into:
        merged_count = merge_into_csv(Path(args.merge_into), kb_rows)
        print(f"Merged rows into {Path(args.merge_into).resolve()}: {merged_count}")

    write_report(
        output_dir / "run_report.json",
        discovered=len(discovered_files),
        extracted=len(extract_results),
        documents=len(clean_documents),
        rows=len(kb_rows),
        skipped=skipped_files,
    )

    print(f"Discovered files: {len(discovered_files)}")
    print(f"Extracted successfully: {len(extract_results)}")
    print(f"Clean documents: {len(clean_documents)}")
    print(f"Knowledge rows: {len(kb_rows)}")
    print(f"Output dir: {output_dir.resolve()}")

if __name__ == "__main__":
    main()
