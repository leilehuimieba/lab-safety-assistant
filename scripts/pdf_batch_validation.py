#!/usr/bin/env python3
"""
Build a PDF validation batch, then export both automated quality signals and
an editable manual review sheet.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import document_ingest_pipeline as dip


STANDARD_PDF_KEYWORDS = [
    "标准",
    "规范",
    "要求",
    "规则",
    "方法",
    "实验室",
    "安全",
    "检测",
    "计量",
    "无损",
    "GB",
    "GBT",
]

MANUAL_FIELDS = [
    "manual_review_status",
    "manual_need_ocr",
    "manual_body_start_correct",
    "manual_cover_toc_skip_correct",
    "manual_rule_action",
    "manual_body_start_page",
    "manual_skip_pages",
    "manual_notes",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def is_standard_pdf(path: Path) -> bool:
    haystack = f"{path.name} {path.parent.name}"
    return any(keyword.lower() in haystack.lower() for keyword in STANDARD_PDF_KEYWORDS)


def discover_standard_pdfs(input_root: Path, limit: int) -> list[Path]:
    all_pdfs = sorted(input_root.rglob("*.pdf"), key=lambda item: str(item).lower())
    standard_pdfs = [path for path in all_pdfs if is_standard_pdf(path)]
    if limit <= 0:
        return all_pdfs

    selected: list[Path] = standard_pdfs[:limit]
    seen = {str(path).lower() for path in selected}
    if len(selected) < limit:
        for path in all_pdfs:
            key = str(path).lower()
            if key in seen:
                continue
            selected.append(path)
            seen.add(key)
            if len(selected) >= limit:
                break
    return selected


def summarize_skipped_pages(skipped_pages: list[dict]) -> str:
    return "; ".join(f"{item['page']}:{item['reason']}" for item in skipped_pages)


def extract_candidate_methods(meta: dict) -> list[str]:
    return [
        item.get("method", "")
        for item in meta.get("pdf_candidate_summaries", [])
        if item.get("method")
    ]


def extract_chosen_summary(meta: dict) -> dict:
    chosen = meta.get("pdf_extractor", "")
    for item in meta.get("pdf_candidate_summaries", []):
        if item.get("method") == chosen:
            return item
    return {}


def compute_garbled_score(meta: dict) -> float:
    summary = extract_chosen_summary(meta)
    short_ratio = float(summary.get("short_line_ratio", 0.0))
    single_ratio = float(summary.get("single_char_ratio", 0.0))
    rare_prefix = int(summary.get("prefix_rare_han_count", 0))
    return round(short_ratio * 70 + single_ratio * 30 + rare_prefix * 3, 2)


def classify_garbled_score(score: float) -> str:
    if score < 8:
        return "low"
    if score < 18:
        return "medium"
    return "high"


def compute_review_priority(row: dict) -> str:
    if (
        row["garbled_level"] == "high"
        or not row["body_start_page"]
        or row["title_patched"]
        or row["ocr_candidate_present"]
        or row["pdf_extractor"] != "pypdf"
    ):
        return "high"
    if row["garbled_level"] == "medium":
        return "medium"
    return "low"


def suggest_need_ocr(row: dict) -> str:
    if row["title_patched"] or row["ocr_candidate_present"]:
        return "yes"
    if row["garbled_level"] != "low" or not row["body_start_page"]:
        return "check"
    return "no"


def suggest_rule_action(row: dict) -> str:
    reasons: list[str] = []
    if row["title_patched"]:
        reasons.append("force_ocr")
    if not row["body_start_page"]:
        reasons.append("body_start_page")
    if row["garbled_level"] == "high" and not row["ocr_candidate_present"]:
        reasons.append("force_ocr")
    if row["body_start_page"] and "cover_page" not in row["skipped_pages"] and row["body_start_page"] >= 3:
        reasons.append("skip_pages")
    seen: list[str] = []
    for item in reasons:
        if item not in seen:
            seen.append(item)
    return ";".join(seen)


def select_review_candidates(rows: list[dict], threshold: float, limit: int) -> list[dict]:
    eligible = [
        row
        for row in rows
        if not row["ocr_candidate_present"]
        and (
            float(row["garbled_score"]) >= threshold
            or row["pdf_extractor"] != "pypdf"
            or not row["body_start_page"]
        )
    ]
    eligible = sorted(
        eligible,
        key=lambda item: (item["pdf_extractor"] == "pypdf", -float(item["garbled_score"]), item["index"]),
    )
    return eligible[:limit]


def build_markdown(rows: list[dict], generated_at: str) -> str:
    reviewed_count = sum(1 for row in rows if row["ocr_reviewed"])
    ocr_candidate_count = sum(1 for row in rows if row["ocr_candidate_present"])
    title_patched_count = sum(1 for row in rows if row["title_patched"])
    high_priority_count = sum(1 for row in rows if row["review_priority"] == "high")

    lines = [
        "# PDF 小批量验收报告 v2",
        "",
        f"- 生成时间: `{generated_at}`",
        f"- 样本数量: `{len(rows)}`",
        f"- 高优先级人工复核: `{high_priority_count}` 份",
        f"- OCR 二次复核: `{reviewed_count}` 份",
        f"- 实际跑出 OCR 候选: `{ocr_candidate_count}` 份",
        f"- 发生标题修补: `{title_patched_count}` 份",
        "",
        "| 序号 | 文件名 | 优先级 | 提取器 | body_start_page | 跳过页 | 乱码分 | 等级 | OCR候选 | OCR复核 | 标题修补 | 建议规则 |",
        "| --- | --- | --- | --- | ---: | --- | ---: | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['index']} | {row['file_name']} | {row['review_priority']} | {row['pdf_extractor']} | "
            f"{row['body_start_page'] or '-'} | {row['skipped_pages'] or '-'} | "
            f"{row['garbled_score']} | {row['garbled_level']} | "
            f"{'Y' if row['ocr_candidate_present'] else '-'} | "
            f"{'Y' if row['ocr_reviewed'] else '-'} | "
            f"{'Y' if row['title_patched'] else '-'} | "
            f"{row['suggest_rule_action'] or '-'} |"
        )

    lines.extend(
        [
            "",
            "## 说明",
            "",
            "- `乱码分` 是启发式风险指标，不代表 OCR 准确率。",
            "- `manual_review_sheet.csv` 是人工标注入口，建议优先处理 `review_priority=high` 的样本。",
            "- 若人工确认某份 PDF 持续需要固定修补，可将结论沉淀到 `data_sources/pdf_special_rules.csv`。",
        ]
    )
    return "\n".join(lines) + "\n"


def build_manual_review_guide(generated_at: str, row_count: int) -> str:
    lines = [
        "# PDF 人工标注说明 v2",
        "",
        f"- 生成时间: `{generated_at}`",
        f"- 待标注文档: `{row_count}` 份",
        "",
        "## 填写建议",
        "",
        "- `manual_need_ocr`: 填 `yes / no / check`，判断是否应长期启用 OCR。",
        "- `manual_body_start_correct`: 填 `yes / no`，判断当前 `body_start_page` 是否正确。",
        "- `manual_cover_toc_skip_correct`: 填 `yes / no / partial`，判断封面、目录、前言页的跳过是否合理。",
        "- `manual_rule_action`: 若需要固化规则，填 `force_ocr / body_start_page / skip_pages / none`。",
        "- `manual_body_start_page`: 若自动识别错误，填写你确认后的正文起始页。",
        "- `manual_skip_pages`: 若需要显式跳过页，填写 `1,2,5-6` 这类页码范围。",
        "",
        "## 推荐流程",
        "",
        "1. 先处理 `review_priority=high` 的样本。",
        "2. 对照源 PDF 核验正文起始页与跳过页。",
        "3. 将稳定结论沉淀进 `pdf_special_rules.csv`，再重新跑统一入库。",
    ]
    return "\n".join(lines) + "\n"


def write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    resolved_fieldnames = fieldnames or (list(rows[0].keys()) if rows else [])
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=resolved_fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_existing_manual_annotations(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        result: dict[str, dict] = {}
        for row in reader:
            file_path = row.get("file_path", "").strip()
            if file_path:
                result[file_path] = {field: row.get(field, "") for field in MANUAL_FIELDS}
        return result


def build_manual_review_sheet(rows: list[dict], existing_annotations: dict[str, dict]) -> list[dict]:
    sheet: list[dict] = []
    for row in rows:
        preserved = existing_annotations.get(row["file_path"], {})
        sheet.append(
            {
                "index": row["index"],
                "review_priority": row["review_priority"],
                "file_name": row["file_name"],
                "file_path": row["file_path"],
                "pdf_special_rule_id": row["pdf_special_rule_id"],
                "pdf_extractor": row["pdf_extractor"],
                "body_start_page": row["body_start_page"],
                "skipped_pages": row["skipped_pages"],
                "garbled_score": row["garbled_score"],
                "garbled_level": row["garbled_level"],
                "ocr_candidate_present": row["ocr_candidate_present"],
                "title_patched": row["title_patched"],
                "review_outcome": row["review_outcome"],
                "suggest_need_ocr": row["suggest_need_ocr"],
                "suggest_rule_action": row["suggest_rule_action"],
                "content_preview": row["content_preview"],
                "manual_review_status": preserved.get("manual_review_status", "pending"),
                "manual_need_ocr": preserved.get("manual_need_ocr", ""),
                "manual_body_start_correct": preserved.get("manual_body_start_correct", ""),
                "manual_cover_toc_skip_correct": preserved.get("manual_cover_toc_skip_correct", ""),
                "manual_rule_action": preserved.get("manual_rule_action", ""),
                "manual_body_start_page": preserved.get("manual_body_start_page", ""),
                "manual_skip_pages": preserved.get("manual_skip_pages", ""),
                "manual_notes": preserved.get("manual_notes", ""),
            }
        )
    return sheet


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a PDF batch and export both auto signals and a manual review sheet."
    )
    parser.add_argument(
        "--input-root",
        default="..\\data",
        help="Root directory that contains PDFs.",
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts\\pdf_validation_batch_v2",
        help="Directory for report and manual review outputs.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="How many standard-like PDFs to include. Use 0 for all matched PDFs.",
    )
    parser.add_argument(
        "--ocr-review-mode",
        "--pdf-ocr-mode",
        dest="ocr_review_mode",
        choices=["auto", "off", "always"],
        default="always",
        help="OCR mode used during targeted second-pass review. Keeps --pdf-ocr-mode as an alias.",
    )
    parser.add_argument(
        "--ocr-review-limit",
        type=int,
        default=2,
        help="How many flagged PDFs should be re-run with OCR review.",
    )
    parser.add_argument(
        "--ocr-review-threshold",
        type=float,
        default=8.0,
        help="Minimum garbled score that triggers second-pass OCR review.",
    )
    parser.add_argument(
        "--pdf-special-rules",
        default="data_sources\\pdf_special_rules.csv",
        help="Optional CSV for per-file PDF extraction overrides.",
    )
    return parser.parse_args()


def get_relative_pdf_path(pdf_path: Path, input_root: Path) -> str:
    try:
        return str(pdf_path.resolve().relative_to(input_root.resolve())).replace("/", "\\")
    except ValueError:
        return pdf_path.name


def get_special_rule_for_path(pdf_path: Path, input_root: Path, pdf_special_rules: list[dict]) -> dict | None:
    rel_path = get_relative_pdf_path(pdf_path, input_root)
    return dip.match_pdf_special_rule(rel_path, pdf_special_rules)


def extract_validation_row(
    index: int,
    pdf_path: Path,
    ocr_mode: str,
    reviewed: bool,
    input_root: Path,
    pdf_special_rules: list[dict],
    baseline_row: dict | None = None,
) -> dict:
    special_rule = get_special_rule_for_path(pdf_path, input_root, pdf_special_rules)
    text, meta = dip.extract_pdf(pdf_path, ocr_mode=ocr_mode, special_rule=special_rule)
    garbled_score = compute_garbled_score(meta)
    candidate_methods = extract_candidate_methods(meta)
    row = {
        "index": index,
        "file_name": pdf_path.name,
        "file_path": str(pdf_path),
        "pdf_extractor": meta.get("pdf_extractor", ""),
        "pdf_special_rule_id": (meta.get("pdf_special_rule") or {}).get("rule_id", ""),
        "body_start_page": meta.get("body_start_page"),
        "page_count": meta.get("page_count"),
        "kept_page_count": meta.get("kept_page_count"),
        "skipped_pages": summarize_skipped_pages(meta.get("skipped_pages", [])),
        "garbled_score": garbled_score,
        "garbled_level": classify_garbled_score(garbled_score),
        "title_patched": bool(meta.get("pdf_ocr_title_patched")),
        "ocr_reviewed": reviewed,
        "ocr_mode_used": ocr_mode,
        "ocr_candidate_present": "ocr" in candidate_methods,
        "candidate_methods": ",".join(candidate_methods),
        "baseline_garbled_score": "",
        "baseline_pdf_extractor": "",
        "score_delta": "",
        "review_outcome": "not_reviewed" if not reviewed else "reviewed",
        "candidate_summaries": json.dumps(
            meta.get("pdf_candidate_summaries", []),
            ensure_ascii=False,
        ),
        "content_preview": text[:280],
    }

    if baseline_row is not None:
        baseline_score = float(baseline_row["garbled_score"])
        score_delta = round(baseline_score - float(garbled_score), 2)
        if row["title_patched"]:
            review_outcome = "title_patched"
        elif score_delta > 0:
            review_outcome = "score_improved"
        elif row["ocr_candidate_present"]:
            review_outcome = "ocr_checked_no_change"
        else:
            review_outcome = "reviewed_without_ocr_candidate"
        row["baseline_garbled_score"] = baseline_score
        row["baseline_pdf_extractor"] = baseline_row["pdf_extractor"]
        row["score_delta"] = score_delta
        row["review_outcome"] = review_outcome

    row["review_priority"] = compute_review_priority(row)
    row["suggest_need_ocr"] = suggest_need_ocr(row)
    row["suggest_rule_action"] = suggest_rule_action(row)
    return row


def main() -> None:
    args = parse_args()
    input_root = Path(args.input_root).resolve()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_special_rules_path = Path(args.pdf_special_rules)
    pdf_special_rules = dip.load_pdf_special_rules(
        pdf_special_rules_path if pdf_special_rules_path.exists() else None
    )

    pdfs = discover_standard_pdfs(input_root, args.limit)
    rows: list[dict] = []
    errors: list[dict] = []

    for index, pdf_path in enumerate(pdfs, start=1):
        try:
            rows.append(
                extract_validation_row(
                    index,
                    pdf_path,
                    ocr_mode="off",
                    reviewed=False,
                    input_root=input_root,
                    pdf_special_rules=pdf_special_rules,
                )
            )
        except Exception as exc:
            errors.append({"file_path": str(pdf_path), "error": str(exc)})

    if args.ocr_review_mode != "off" and args.ocr_review_limit > 0:
        review_candidates = select_review_candidates(
            rows,
            threshold=args.ocr_review_threshold,
            limit=args.ocr_review_limit,
        )
        reviewed_map = {row["index"]: row for row in rows}
        for row in review_candidates:
            pdf_path = Path(row["file_path"])
            try:
                reviewed_row = extract_validation_row(
                    row["index"],
                    pdf_path,
                    ocr_mode=args.ocr_review_mode,
                    reviewed=True,
                    input_root=input_root,
                    pdf_special_rules=pdf_special_rules,
                    baseline_row=row,
                )
                reviewed_map[row["index"]] = reviewed_row
            except Exception as exc:
                errors.append({"file_path": str(pdf_path), "error": f"OCR review failed: {exc}"})
        rows = [reviewed_map[index] for index in sorted(reviewed_map)]

    generated_at = now_iso()
    write_csv(output_dir / "validation_report.csv", rows)
    (output_dir / "validation_report.md").write_text(
        build_markdown(rows, generated_at),
        encoding="utf-8",
    )
    (output_dir / "validation_report.json").write_text(
        json.dumps(
            {
                "generated_at": generated_at,
                "sample_count": len(rows),
                "error_count": len(errors),
                "reviewed_count": sum(1 for row in rows if row["ocr_reviewed"]),
                "ocr_candidate_count": sum(1 for row in rows if row["ocr_candidate_present"]),
                "title_patched_count": sum(1 for row in rows if row["title_patched"]),
                "rows": rows,
                "errors": errors,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    manual_sheet_path = output_dir / "manual_review_sheet.csv"
    existing_annotations = load_existing_manual_annotations(manual_sheet_path)
    manual_rows = build_manual_review_sheet(rows, existing_annotations)
    write_csv(manual_sheet_path, manual_rows)
    (output_dir / "manual_review_guide.md").write_text(
        build_manual_review_guide(generated_at, len(manual_rows)),
        encoding="utf-8",
    )

    print(f"Validated PDFs: {len(rows)}")
    print(f"Validation output: {output_dir.resolve()}")
    print(f"Manual review sheet: {manual_sheet_path.resolve()}")
    if errors:
        print(f"Errors: {len(errors)}")


if __name__ == "__main__":
    main()
