#!/usr/bin/env python3
"""
Generate weekly team report markdown from git history and repository snapshots.
"""

from __future__ import annotations

import argparse
import csv
import subprocess
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate weekly team report markdown.")
    parser.add_argument("--repo-root", default=".", help="Repository root path.")
    parser.add_argument("--since", default="7 days ago", help="git --since value.")
    parser.add_argument("--until", default="now", help="git --until value.")
    parser.add_argument(
        "--output",
        default="",
        help="Output markdown path. Default: docs/weekly_reports/weekly_report_<YYYYMMDD>.md",
    )
    parser.add_argument(
        "--max-commits",
        type=int,
        default=20,
        help="Maximum recent commits listed in report.",
    )
    return parser.parse_args()


def run_git(repo_root: Path, args: list[str]) -> str:
    cmd = ["git", "-C", str(repo_root), *args]
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"git command failed: {' '.join(args)}\n{completed.stderr.strip()}")
    return completed.stdout


def count_csv_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return sum(1 for _ in reader)


def parse_release_entries(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    lines = path.read_text(encoding="utf-8").splitlines()
    filtered: list[str] = []
    in_code = False
    for ln in lines:
        if ln.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        filtered.append(ln)

    indices = [i for i, ln in enumerate(filtered) if ln.startswith("## 发布批次：")]
    entries: list[dict[str, str]] = []
    for idx, start in enumerate(indices):
        end = indices[idx + 1] if idx + 1 < len(indices) else len(filtered)
        block = filtered[start:end]
        entry: dict[str, str] = {
            "batch": block[0].replace("## 发布批次：", "").strip()
        }
        for ln in block[1:]:
            if not ln.strip().startswith("- "):
                continue
            if "：" not in ln:
                continue
            left, right = ln.split("：", 1)
            key = left.replace("- ", "").strip()
            entry[key] = right.strip()
        entries.append(entry)
    return entries


def collect_commit_data(repo_root: Path, since: str, until: str) -> dict:
    out = run_git(
        repo_root,
        [
            "log",
            f"--since={since}",
            f"--until={until}",
            "--date=short",
            "--pretty=format:@@@%h|%ad|%an|%s",
            "--name-only",
        ],
    )

    commits: list[dict] = []
    current: dict | None = None
    for ln in out.splitlines():
        if ln.startswith("@@@"):
            if current:
                commits.append(current)
            _, payload = ln[:3], ln[3:]
            parts = payload.split("|", 3)
            if len(parts) != 4:
                continue
            current = {
                "hash": parts[0],
                "date": parts[1],
                "author": parts[2],
                "subject": parts[3],
                "files": [],
            }
        elif ln.strip() and current is not None:
            current["files"].append(ln.strip())
    if current:
        commits.append(current)

    contributors = sorted({c["author"] for c in commits})
    category_hits = defaultdict(int)

    for c in commits:
        files = set(c["files"])
        if any(
            f.startswith("data_sources/document_manifest")
            or f.startswith("data_sources/web_seed_urls")
            for f in files
        ):
            category_hits["collection_commits"] += 1
        if any(
            f.startswith("data_sources/pdf_special_rules")
            or f.startswith("scripts/run_pdf_batch_check")
            or f.startswith("scripts/run_unified_batch")
            for f in files
        ):
            category_hits["cleaning_commits"] += 1
        if any(
            f.startswith("docs/eval/release_review_log")
            or f.startswith("scripts/generate_release_review_entry")
            for f in files
        ):
            category_hits["release_commits"] += 1
        if any(f.startswith("docs/") for f in files):
            category_hits["docs_commits"] += 1

    return {
        "commits": commits,
        "contributors": contributors,
        "category_hits": category_hits,
    }


def render_report(
    *,
    since: str,
    until: str,
    generated_at: str,
    commit_data: dict,
    manifest_rows: int,
    web_rows: int,
    pdf_rules_rows: int,
    latest_release: dict[str, str] | None,
    max_commits: int,
) -> str:
    commits: list[dict] = commit_data["commits"]
    contributors: list[str] = commit_data["contributors"]
    hits = commit_data["category_hits"]

    lines: list[str] = []
    lines.append(f"# 周报（自动）{generated_at[:10]}")
    lines.append("")
    lines.append(f"- 统计区间：`{since}` -> `{until}`")
    lines.append(f"- 生成时间：`{generated_at}`")
    lines.append("")
    lines.append("## 1. 协作活跃度")
    lines.append("")
    lines.append(f"- 本周提交数：`{len(commits)}`")
    lines.append(f"- 活跃贡献者：`{len(contributors)}` ({', '.join(contributors) if contributors else '无'})")
    lines.append(f"- 数据收集相关提交：`{hits.get('collection_commits', 0)}`")
    lines.append(f"- 清洗相关提交：`{hits.get('cleaning_commits', 0)}`")
    lines.append(f"- 发布验收相关提交：`{hits.get('release_commits', 0)}`")
    lines.append("")
    lines.append("## 2. 数据规模快照")
    lines.append("")
    lines.append(f"- `document_manifest.csv` 行数：`{manifest_rows}`")
    lines.append(f"- `web_seed_urls.csv` 行数：`{web_rows}`")
    lines.append(f"- `pdf_special_rules.csv` 规则数：`{pdf_rules_rows}`")
    lines.append("")
    lines.append("## 3. 最近提交摘要")
    lines.append("")
    if not commits:
        lines.append("- 本周无提交。")
    else:
        for c in commits[:max_commits]:
            lines.append(f"- `{c['hash']}` {c['date']} {c['author']} - {c['subject']}")
    lines.append("")
    lines.append("## 4. 最新发布验收状态")
    lines.append("")
    if latest_release:
        lines.append(f"- 批次：`{latest_release.get('batch', 'unknown')}`")
        lines.append(f"- 审核日期：`{latest_release.get('审核日期', '')}`")
        lines.append(f"- 审核人：`{latest_release.get('审核人A', '')}` / `{latest_release.get('审核人B', '')}`")
        lines.append(f"- 人工审核题数：`{latest_release.get('人工审核题数', '')}`")
        lines.append(f"- 通过题数：`{latest_release.get('通过题数', '')}`")
        lines.append(f"- 高风险错误建议：`{latest_release.get('高风险错误建议（0/1+）', '')}`")
        lines.append(f"- 发布结论：`{latest_release.get('结论（允许发布 yes/no）', '')}`")
    else:
        lines.append("- 暂无正式发布验收记录。")
    lines.append("")
    lines.append("## 5. 下周建议（自动）")
    lines.append("")

    if manifest_rows < 50:
        lines.append("- 建议优先补齐 `P0/P1` 数据来源，当前文档规模偏小。")
    if hits.get("collection_commits", 0) == 0:
        lines.append("- 本周缺少数据收集提交，建议至少安排 1 名同学专项补数。")
    if hits.get("cleaning_commits", 0) == 0:
        lines.append("- 本周缺少清洗提交，建议固定每周执行一次 PDF 体检与统一入库。")
    if not latest_release:
        lines.append("- 建议本周至少完成一次发布验收记录，形成可追溯闭环。")
    elif latest_release.get("结论（允许发布 yes/no）", "").lower() != "yes":
        lines.append("- 最新验收结论为 `no`，建议优先关闭高风险问题后再发布。")
    else:
        lines.append("- 流程运行正常，可继续扩展数据覆盖面并保持周度验收节奏。")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()

    today = datetime.now().strftime("%Y%m%d")
    output = (
        Path(args.output)
        if args.output
        else repo_root / "docs" / "weekly_reports" / f"weekly_report_{today}.md"
    )
    if not output.is_absolute():
        output = repo_root / output
    output.parent.mkdir(parents=True, exist_ok=True)

    manifest_rows = count_csv_rows(repo_root / "data_sources" / "document_manifest.csv")
    web_rows = count_csv_rows(repo_root / "data_sources" / "web_seed_urls.csv")
    pdf_rules_rows = count_csv_rows(repo_root / "data_sources" / "pdf_special_rules.csv")
    release_entries = parse_release_entries(repo_root / "docs" / "eval" / "release_review_log.md")
    latest_release = release_entries[-1] if release_entries else None
    commit_data = collect_commit_data(repo_root, args.since, args.until)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report = render_report(
        since=args.since,
        until=args.until,
        generated_at=generated_at,
        commit_data=commit_data,
        manifest_rows=manifest_rows,
        web_rows=web_rows,
        pdf_rules_rows=pdf_rules_rows,
        latest_release=latest_release,
        max_commits=args.max_commits,
    )

    output.write_text(report, encoding="utf-8")
    print(f"Generated weekly report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
