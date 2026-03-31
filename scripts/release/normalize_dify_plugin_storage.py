#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


BAD_COLON_CHARS = {
    "\uf03a",
    "\uff1a",
    "\ufe13",
    "\ufe55",
    "\u2236",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize Dify plugin storage directory names.")
    parser.add_argument(
        "--storage-root",
        default="/root/dify_sync/docker/volumes/plugin_daemon",
        help="Root directory of the plugin_daemon storage bind mount.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply renames. Default is dry-run.",
    )
    return parser.parse_args()


def normalize_name(name: str) -> str:
    fixed = name
    for bad in BAD_COLON_CHARS:
        fixed = fixed.replace(bad, ":")
    return fixed


def collect_renames(storage_root: Path) -> list[dict[str, str]]:
    renames: list[dict[str, str]] = []
    for bucket_name in ("plugin", "plugin_packages"):
        bucket = storage_root / bucket_name
        if not bucket.is_dir():
            continue
        for namespace_dir in sorted(bucket.iterdir()):
            if not namespace_dir.is_dir():
                continue
            for item in sorted(namespace_dir.iterdir()):
                fixed_name = normalize_name(item.name)
                if fixed_name == item.name:
                    continue
                renames.append(
                    {
                        "bucket": bucket_name,
                        "from": str(item),
                        "to": str(item.with_name(fixed_name)),
                    }
                )
    return renames


def main() -> int:
    args = parse_args()
    storage_root = Path(args.storage_root).resolve()
    payload = {
        "storage_root": str(storage_root),
        "apply": args.apply,
        "renamed": [],
        "skipped": [],
    }

    if not storage_root.exists():
        payload["error"] = f"storage root not found: {storage_root}"
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2

    renames = collect_renames(storage_root)
    for entry in renames:
        source = Path(entry["from"])
        target = Path(entry["to"])
        if target.exists():
            payload["skipped"].append(
                {
                    "from": str(source),
                    "to": str(target),
                    "reason": "target_exists",
                }
            )
            continue
        if args.apply:
            source.rename(target)
        payload["renamed"].append({"from": str(source), "to": str(target)})

    payload["rename_count"] = len(payload["renamed"])
    payload["skip_count"] = len(payload["skipped"])
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
