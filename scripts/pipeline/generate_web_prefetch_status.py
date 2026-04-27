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


def parse_int(raw: str | int | float | None) -> int | None:
    if raw is None:
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float):
        return int(raw)
    text = str(raw).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def parse_float(raw: str | int | float | None, default: float = 0.0) -> float:
    if raw is None:
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def normalize_status(fetch_status: str, status: str, error: str, status_code: int | None, quality_score: float) -> str:
    fs = (fetch_status or "").strip().lower()
    st = (status or "").strip().lower()
    err = (error or "").strip().lower()
    sc = status_code if status_code is not None else 0

    if sc in {401, 403, 407}:
        return "blocked"
    if sc in {404, 410}:
        return "not_found"
    if sc >= 500:
        return "error"
    if sc >= 400:
        return "error"

    if fs in {"ok", "success"} and st == "success":
        # Guard against false-positive success pages with no useful body.
        if quality_score <= 0.0:
            return "blocked"
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
        status_code = parse_int(info.get("status_code") if info else None)
        quality_value = parse_float(quality_score if info else 0.0, default=0.0)

        output_rows.append(
            {
                "source_id": source_id,
                "title": row.get("title", ""),
                "url": row.get("url", ""),
                "status": normalize_status(
                    str(info.get("fetch_status") or ""),
                    str(info.get("status") or ""),
                    str(info.get("error") or ""),
                    status_code,
                    quality_value,
                )
                if info
                else "not_fetched",
                "fetch_status": str(info.get("fetch_status") or ""),
                "provider": str(info.get("provider") or ""),
                "status_code": str(status_code or ""),
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
