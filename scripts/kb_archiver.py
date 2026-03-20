#!/usr/bin/env python3
"""
Knowledge Base Version Archiver

This script creates versioned snapshots of the knowledge base for archival purposes.
Snapshots are named with the pattern: knowledge_base_YYYYMM.csv

Usage:
    python kb_archiver.py [command]

Commands:
    archive     - Create a new archive of the current knowledge base
    list        - List all existing archives
    restore     - Restore from an archive (requires --archive argument)
    validate    - Validate an archive file
"""

import argparse
import csv
import shutil
import sys
from datetime import datetime
from pathlib import Path


ARCHIVES_DIR = Path("artifacts/kb_archives")
ARCHIVE_PREFIX = "knowledge_base_"
ARCHIVE_SUFFIX = ".csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="KB Version Archiver")
    parser.add_argument(
        "--kb-path",
        type=Path,
        default=Path("knowledge_base_curated.csv"),
        help="Path to current knowledge base",
    )
    parser.add_argument(
        "--archives-dir",
        type=Path,
        default=ARCHIVES_DIR,
        help="Directory to store archives",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    archive_parser = subparsers.add_parser("archive", help="Create a new archive")
    archive_parser.add_argument(
        "--tag",
        default="",
        help="Optional tag for this archive (e.g., 'before-major-update')",
    )

    list_parser = subparsers.add_parser("list", help="List existing archives")

    restore_parser = subparsers.add_parser("restore", help="Restore from archive")
    restore_parser.add_argument(
        "--archive",
        type=Path,
        required=True,
        help="Archive file to restore from",
    )
    restore_parser.add_argument(
        "--output",
        type=Path,
        default=Path("knowledge_base_curated.csv"),
        help="Output path for restored file",
    )

    validate_parser = subparsers.add_parser("validate", help="Validate an archive")
    validate_parser.add_argument(
        "--archive",
        type=Path,
        required=True,
        help="Archive file to validate",
    )

    return parser.parse_args()


def get_archive_name(kb_path: Path, tag: str = "") -> str:
    now = datetime.now()
    version = now.strftime("%Y%m")
    if tag:
        version = f"{version}-{tag}"
    archive_name = f"{ARCHIVE_PREFIX}{version}{ARCHIVE_SUFFIX}"
    return archive_name


def count_entries(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            return sum(1 for _ in reader)
    except Exception:
        return 0


def archive_kb(kb_path: Path, archives_dir: Path, tag: str = "") -> Path:
    if not kb_path.exists():
        print(f"Error: Knowledge base not found: {kb_path}")
        sys.exit(1)

    archives_dir.mkdir(parents=True, exist_ok=True)

    archive_name = get_archive_name(kb_path, tag)
    archive_path = archives_dir / archive_name

    shutil.copy2(kb_path, archive_path)

    entry_count = count_entries(archive_path)
    file_size = archive_path.stat().st_size

    print(f"Archived: {archive_path}")
    print(f"  Entries: {entry_count}")
    print(f"  Size: {file_size:,} bytes")

    return archive_path


def list_archives(archives_dir: Path) -> None:
    if not archives_dir.exists():
        print("No archives found")
        return

    archives = sorted(archives_dir.glob(f"{ARCHIVE_PREFIX}*{ARCHIVE_SUFFIX}"))

    if not archives:
        print("No archives found")
        return

    print("=" * 60)
    print("Knowledge Base Archives")
    print("=" * 60)

    for archive in archives:
        entry_count = count_entries(archive)
        file_size = archive.stat().st_size
        modified = datetime.fromtimestamp(archive.stat().st_mtime).strftime("%Y-%m-%d %H:%M")

        tag = archive.stem.replace(ARCHIVE_PREFIX, "")
        print(f"\n{tag}")
        print(f"  Path: {archive}")
        print(f"  Entries: {entry_count}")
        print(f"  Size: {file_size:,} bytes")
        print(f"  Modified: {modified}")

    print("\n" + "=" * 60)
    print(f"Total: {len(archives)} archives")


def validate_archive(archive_path: Path) -> bool:
    if not archive_path.exists():
        print(f"Error: Archive not found: {archive_path}")
        return False

    try:
        with archive_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            rows = list(reader)

        print(f"Archive validation: {archive_path}")
        print(f"  Headers: {len(headers) if headers else 0} columns")
        print(f"  Entries: {len(rows)}")

        required_headers = ["id", "title", "category", "question", "answer"]
        missing = [h for h in required_headers if h not in (headers or [])]
        if missing:
            print(f"  Warning: Missing required headers: {missing}")
            return False

        print("  Status: Valid")
        return True

    except Exception as e:
        print(f"  Status: Invalid - {e}")
        return False


def restore_archive(archive_path: Path, output_path: Path) -> None:
    if not archive_path.exists():
        print(f"Error: Archive not found: {archive_path}")
        sys.exit(1)

    is_valid = validate_archive(archive_path)
    if not is_valid:
        print("Warning: Archive validation failed, but continuing with restore...")

    shutil.copy2(archive_path, output_path)
    print(f"Restored: {output_path}")


def main() -> int:
    args = parse_args()

    if args.command == "archive":
        archive_kb(args.kb_path, args.archives_dir, args.tag)

    elif args.command == "list":
        list_archives(args.archives_dir)

    elif args.command == "restore":
        restore_archive(args.archive, args.output)

    elif args.command == "validate":
        validate_archive(args.archive)

    else:
        print("Usage: python kb_archiver.py [archive|list|restore|validate]")
        print("Run without arguments to create an archive of the current KB")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
