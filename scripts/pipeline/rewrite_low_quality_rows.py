#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import ai_review_kb as ark


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Auto-rewrite low-quality KB rows into structured safety format."
    )
    parser.add_argument("--input-csv", required=True, help="Input knowledge_base_web.csv path.")
    parser.add_argument("--status-csv", required=True, help="Prefetch status CSV path.")
    parser.add_argument("--output-csv", required=True, help="Rewritten output CSV path.")
    parser.add_argument("--log-csv", required=True, help="Rewrite log CSV path.")
    parser.add_argument(
        "--low-quality-threshold",
        type=float,
        default=0.70,
        help="Rows below this score will be rewritten.",
    )
    return parser.parse_args()


def clean_text(raw: str, max_len: int = 1200) -> str:
    text = (raw or "").strip()
    if "Markdown Content:" in text:
        text = text.split("Markdown Content:", 1)[1]
    text = re.sub(r"%PDF-\d\.\d", " ", text)
    text = re.sub(r"endobj|stream|endstream|xref|trailer", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        text = text[:max_len].rstrip() + " ..."
    return text


def source_id_from_row_id(row_id: str) -> str:
    parts = (row_id or "").split("-")
    if len(parts) >= 2:
        return f"{parts[0]}-{parts[1]}"
    return row_id or ""


def read_status_scores(path: Path) -> dict[str, float]:
    out: dict[str, float] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            source_id = (row.get("source_id") or "").strip()
            if not source_id:
                continue
            try:
                score = float((row.get("quality_score") or "0").strip())
            except ValueError:
                score = 0.0
            out[source_id] = score
    return out


def ppe_from_hazard(hazard_types: str) -> str:
    h = (hazard_types or "").lower()
    ppe: list[str] = []
    if any(k in h for k in ["chemical", "hazardous_chemicals", "corrosive"]):
        ppe.extend(["safety goggles", "chemical-resistant gloves", "lab coat"])
    if "biosafety" in h:
        ppe.extend(["lab coat", "protective gloves", "surgical mask or respirator"])
    if "electrical" in h:
        ppe.extend(["insulated gloves", "insulated footwear"])
    if not ppe:
        ppe.extend(["safety goggles", "protective gloves", "lab coat"])
    dedup: list[str] = []
    for item in ppe:
        if item not in dedup:
            dedup.append(item)
    return "; ".join(dedup)


def structured_steps() -> str:
    return (
        "1) Confirm the experiment scope, SOP, and approval requirements before operation.\n"
        "2) Verify facilities (ventilation, containment, warning signs) and PPE readiness.\n"
        "3) Execute operation with buddy-check, maintain records, and control exposure paths.\n"
        "4) Handle samples/waste by classification and complete decontamination after use.\n"
        "5) Report abnormalities immediately and trigger emergency response when needed."
    )


def rewrite_row(row: dict[str, str]) -> dict[str, str]:
    title = (row.get("title") or "").strip()
    question = (row.get("question") or "").strip()
    source_title = (row.get("source_title") or title).strip()
    source_url = (row.get("source_url") or "").strip()
    cleaned = clean_text(row.get("answer") or "")
    row["answer"] = (
        f"Based on the referenced safety document '{source_title}', this item requires risk-based controls "
        "for laboratory activities, including training access, containment conditions, PPE usage, "
        "waste control, and emergency response readiness. "
        f"Applicable scenario: {question or title}. "
        f"Key extracted context: {cleaned}"
    ).strip()
    row["steps"] = structured_steps()
    row["ppe"] = ppe_from_hazard(row.get("hazard_types") or "")
    row["forbidden"] = (
        "Do not perform high-risk procedures without training/authorization; "
        "do not bypass containment and engineering controls; "
        "do not operate alone in hazardous scenarios."
    )
    row["disposal"] = (
        "Classify and package laboratory waste by hazard type, label clearly, "
        "and transfer through approved disposal workflow."
    )
    row["first_aid"] = (
        "For exposure or injury, stop operation immediately, perform on-site first aid "
        "(flush/decontaminate/isolate), and seek medical support without delay."
    )
    row["emergency"] = (
        "Stop operation, isolate area, notify supervisor and EHS team, "
        "and execute the institutional emergency plan."
    )
    row["references"] = source_title if not source_url else f"{source_title} | {source_url}"
    tags = (row.get("tags") or "").strip()
    if "auto_rewrite_low_quality" not in tags:
        row["tags"] = (tags + ";auto_rewrite_low_quality").strip(";")
    return row


def main() -> int:
    args = parse_args()
    input_csv = Path(args.input_csv).resolve()
    status_csv = Path(args.status_csv).resolve()
    output_csv = Path(args.output_csv).resolve()
    log_csv = Path(args.log_csv).resolve()

    if not input_csv.exists():
        raise SystemExit(f"Input CSV not found: {input_csv}")
    if not status_csv.exists():
        raise SystemExit(f"Status CSV not found: {status_csv}")

    score_map = read_status_scores(status_csv)
    rewritten_rows: list[dict[str, str]] = []
    logs: list[dict[str, str]] = []

    with input_csv.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        rid = (row.get("id") or "").strip()
        source_id = source_id_from_row_id(rid)
        score = score_map.get(source_id, 1.0)
        rewritten = "no"
        if score < args.low_quality_threshold:
            row = rewrite_row(row)
            rewritten = "yes"
        normalized = {field: (row.get(field) or "").strip() for field in ark.KB_FIELDNAMES}
        rewritten_rows.append(normalized)
        logs.append(
            {
                "id": rid,
                "source_id": source_id,
                "quality_score": f"{score:.4f}",
                "rewritten": rewritten,
            }
        )

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ark.KB_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rewritten_rows)

    log_csv.parent.mkdir(parents=True, exist_ok=True)
    with log_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "source_id", "quality_score", "rewritten"])
        writer.writeheader()
        writer.writerows(logs)

    rewrite_count = sum(1 for x in logs if x["rewritten"] == "yes")
    print(f"Rewritten rows: {rewrite_count}/{len(logs)}")
    print(f"Output CSV: {output_csv}")
    print(f"Rewrite log: {log_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
