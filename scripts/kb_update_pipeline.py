#!/usr/bin/env python3
"""
Knowledge Base Update Pipeline

This script orchestrates the complete KB update workflow:
1. Web content fetching (optional)
2. Data cleaning and deduplication
3. Traceability enhancement
4. Manual review preparation
5. Quality gate validation

Usage:
    python kb_update_pipeline.py [command]

Commands:
    full       - Run the complete pipeline
    fetch      - Fetch new content from web sources
    clean      - Clean and deduplicate entries
    validate   - Run quality gate validation
    archive    - Create archive before update
"""

import argparse
import csv
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    
    if result.returncode != 0:
        print(f"ERROR: {description} failed with return code {result.returncode}")
        return False
    
    print(f"SUCCESS: {description} completed")
    return True


def run_pipeline_step(script: str, args: list[str], description: str) -> bool:
    cmd = ["python3", f"scripts/{script}"] + args
    return run_command(cmd, description)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="KB Update Pipeline")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    full_parser = subparsers.add_parser("full", help="Run complete pipeline")
    full_parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help="Skip web content fetching step"
    )

    subparsers.add_parser("fetch", help="Fetch new content from web sources")
    subparsers.add_parser("clean", help="Clean and deduplicate entries")
    subparsers.add_parser("validate", help="Run quality gate validation")
    subparsers.add_parser("archive", help="Create archive before update")

    return parser.parse_args()


def step_fetch() -> bool:
    return run_pipeline_step(
        "web_ingest_pipeline.py",
        ["--mode", "auto"],
        "Fetching web content"
    )


def step_clean() -> bool:
    return run_pipeline_step(
        "_clean_web_entries.py",
        [],
        "Cleaning and deduplicating entries"
    )


def step_validate() -> bool:
    return run_pipeline_step(
        "quality_gate.py",
        [],
        "Running quality gate validation"
    )


def step_archive() -> bool:
    return run_pipeline_step(
        "kb_archiver.py",
        ["archive"],
        "Creating KB archive"
    )


def run_full_pipeline(skip_fetch: bool = False) -> bool:
    print("\n" + "="*60)
    print("KNOWLEDGE BASE UPDATE PIPELINE")
    print("="*60)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    steps = []

    if not skip_fetch:
        steps.append(("fetch", lambda: step_fetch()))

    steps.append(("archive", step_archive))
    steps.append(("clean", step_clean))
    steps.append(("validate", step_validate))

    failed_step = None
    for step_name, step_func in steps:
        print(f"\n>>> Step: {step_name}")
        if not step_func():
            failed_step = step_name
            break

    print("\n" + "="*60)
    print("PIPELINE SUMMARY")
    print("="*60)
    
    if failed_step:
        print(f"FAILED at step: {failed_step}")
        return False
    else:
        print("ALL STEPS COMPLETED SUCCESSFULLY")
        print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return True


def main() -> int:
    args = parse_args()

    if args.command == "full":
        success = run_full_pipeline(skip_fetch=args.skip_fetch)
    elif args.command == "fetch":
        success = step_fetch()
    elif args.command == "clean":
        success = step_clean()
    elif args.command == "validate":
        success = step_validate()
    elif args.command == "archive":
        success = step_archive()
    else:
        print("Usage: python kb_update_pipeline.py [full|fetch|clean|validate|archive]")
        print("\nPipeline Commands:")
        print("  full     - Run complete pipeline (fetch -> archive -> clean -> validate)")
        print("  fetch    - Fetch new content from web sources")
        print("  clean    - Clean and deduplicate entries")
        print("  validate - Run quality gate validation")
        print("  archive  - Create archive before update")
        return 0

    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
