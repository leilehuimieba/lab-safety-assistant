#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build relink-success candidate KB CSV from status + knowledge CSVs.")
    parser.add_argument("--map-csv", required=True, help="Relink map CSV containing source_id column.")
    parser.add_argument(
        "--status-csv",
        action="append",
        required=True,
        help="Prefetch status CSV path. Repeat this arg for multiple files.",
    )
    parser.add_argument(
        "--kb-csv",
        action="append",
        required=True,
        help="Knowledge-base CSV path. Repeat this arg for multiple files.",
    )
    parser.add_argument("--output-csv", required=True, help="Output CSV for rows whose source_id relinked and status=ok.")
    parser.add_argument(
        "--id-status-csv",
        required=True,
        help="Output CSV for relink source_id status snapshot.",
    )
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def row_source_id(row_id: str) -> str:
    raw = (row_id or "").strip()
    if "-" in raw:
        return raw.rsplit("-", 1)[0]
    return raw


def main() -> int:
    args = parse_args()
    map_csv = Path(args.map_csv).resolve()
    status_paths = [Path(p).resolve() for p in args.status_csv]
    kb_paths = [Path(p).resolve() for p in args.kb_csv]
    output_csv = Path(args.output_csv).resolve()
    id_status_csv = Path(args.id_status_csv).resolve()

    if not map_csv.exists():
        raise SystemExit(f"Map CSV not found: {map_csv}")
    for path in status_paths + kb_paths:
        if not path.exists():
            raise SystemExit(f"Input CSV not found: {path}")

    relink_rows = read_rows(map_csv)
    relink_ids = sorted({(row.get("source_id") or "").strip() for row in relink_rows if (row.get("source_id") or "").strip()})
    if not relink_ids:
        raise SystemExit(f"No source_id found in map CSV: {map_csv}")

    status_map: dict[str, str] = {}
    for path in status_paths:
        for row in read_rows(path):
            sid = (row.get("source_id") or "").strip()
            if sid and sid in relink_ids:
                status_map[sid] = (row.get("status") or "").strip().lower()

    ok_ids = {sid for sid in relink_ids if status_map.get(sid) == "ok"}

    output_rows: list[dict[str, str]] = []
    fieldnames: list[str] | None = None
    for path in kb_paths:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if fieldnames is None:
                fieldnames = reader.fieldnames or []
            for row in reader:
                sid = row_source_id(row.get("id", ""))
                if sid in ok_ids:
                    output_rows.append(row)

    if fieldnames is None:
        raise SystemExit("No KB rows found in kb-csv inputs.")

    write_rows(output_csv, fieldnames, output_rows)
    id_status_rows = [{"source_id": sid, "status": status_map.get(sid, "missing")} for sid in relink_ids]
    write_rows(id_status_csv, ["source_id", "status"], id_status_rows)

    print("Relink success candidates generated:")
    print(f"- map: {map_csv}")
    print(f"- relink_ids: {len(relink_ids)}")
    print(f"- ok_ids: {len(ok_ids)}")
    print(f"- output_csv: {output_csv}")
    print(f"- id_status_csv: {id_status_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

