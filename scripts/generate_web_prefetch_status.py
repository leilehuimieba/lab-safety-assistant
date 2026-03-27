#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate prefetch status CSV from manifest + fetch_results.jsonl.")
    parser.add_argument("--manifest", required=True, help="Seed manifest CSV.")
    parser.add_argument("--fetch-results", required=True, help="fetch_results.jsonl path.")
    parser.add_argument("--output", required=True, help="Output status CSV path.")
    return parser.parse_args()


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_fetch_results(path: Path) -> dict[str, dict]:
    mapping: dict[str, dict] = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            source_id = str(payload.get("source_id") or "").strip()
            if not source_id:
                continue
            mapping[source_id] = payload
    return mapping


def normalize_status(fetch_status: str, status: str, error: str) -> str:
    fs = (fetch_status or "").strip().lower()
    st = (status or "").strip().lower()
    err = (error or "").strip().lower()
    if fs in {"ok", "success"} and st == "success":
        return "ok"
    if fs in {"blocked"}:
        return "blocked"
    if "timeout" in err:
        return "timeout"
    if "404" in err:
        return "not_found"
    if st == "error":
        return "error"
    return fs or st or "unknown"


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest).resolve()
    fetch_results_path = Path(args.fetch_results).resolve()
    output_path = Path(args.output).resolve()

    if not manifest_path.exists():
        raise SystemExit(f"Manifest not found: {manifest_path}")
    if not fetch_results_path.exists():
        raise SystemExit(f"Fetch results not found: {fetch_results_path}")

    manifest_rows = read_manifest(manifest_path)
    fetched = read_fetch_results(fetch_results_path)

    output_rows: list[dict[str, str]] = []
    for row in manifest_rows:
        source_id = (row.get("source_id") or "").strip()
        info = fetched.get(source_id, {})
        quality_score = info.get("quality_score", "")
        quality_text = ""
        if isinstance(quality_score, (float, int)):
            quality_text = f"{float(quality_score):.4f}"
        elif isinstance(quality_score, str) and quality_score.strip():
            quality_text = quality_score.strip()

        output_rows.append(
            {
                "source_id": source_id,
                "title": row.get("title", ""),
                "url": row.get("url", ""),
                "status": normalize_status(
                    str(info.get("fetch_status") or ""),
                    str(info.get("status") or ""),
                    str(info.get("error") or ""),
                )
                if info
                else "not_fetched",
                "fetch_status": str(info.get("fetch_status") or ""),
                "provider": str(info.get("provider") or ""),
                "status_code": str(info.get("status_code") or ""),
                "quality_score": quality_text,
                "error": str(info.get("error") or ""),
                "final_url": str(info.get("final_url") or ""),
                "fetched_at": str(info.get("fetched_at") or ""),
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "source_id",
        "title",
        "url",
        "status",
        "fetch_status",
        "provider",
        "status_code",
        "quality_score",
        "error",
        "final_url",
        "fetched_at",
    ]
    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    ok_count = sum(1 for item in output_rows if item["status"] == "ok")
    print(f"Prefetch status generated: {output_path}")
    print(f"- total: {len(output_rows)}")
    print(f"- ok: {ok_count}")
    print(f"- non_ok: {len(output_rows) - ok_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

