#!/usr/bin/env python3
"""
Generate weekly gate operations report from GitHub alert issues.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


TITLE_DATE_PATTERN = re.compile(r"^\[Eval Gate\] (\d{4}-\d{2}-\d{2}) gate failed$")


@dataclass
class Issue:
    number: int
    title: str
    state: str
    created_at: datetime
    updated_at: datetime
    labels: set[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate weekly gate ops markdown report.")
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument(
        "--output",
        default="docs/eval/weekly_gate_ops.md",
        help="Output markdown path.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Rolling day window for summary.",
    )
    parser.add_argument(
        "--repo",
        default=os.environ.get("GITHUB_REPOSITORY", ""),
        help="GitHub repository in owner/name format.",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("GITHUB_TOKEN", ""),
        help="GitHub token. If empty, use --issues-json.",
    )
    parser.add_argument(
        "--issues-json",
        default="",
        help="Optional local issues json for offline generation/testing.",
    )
    parser.add_argument(
        "--today",
        default="",
        help="Optional override date in YYYY-MM-DD (for testing).",
    )
    return parser.parse_args()


def parse_dt(value: str) -> datetime:
    raw = (value or "").strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    return datetime.fromisoformat(raw).astimezone(timezone.utc)


def parse_issue(item: dict[str, Any]) -> Issue | None:
    if "pull_request" in item:
        return None
    labels_raw = item.get("labels", [])
    labels: set[str] = set()
    if isinstance(labels_raw, list):
        for label in labels_raw:
            if isinstance(label, dict):
                name = str(label.get("name", "")).strip()
                if name:
                    labels.add(name)
            elif isinstance(label, str):
                name = label.strip()
                if name:
                    labels.add(name)
    try:
        number = int(item.get("number", 0) or 0)
        title = str(item.get("title", "") or "").strip()
        state = str(item.get("state", "") or "").strip().lower()
        created_at = parse_dt(str(item.get("created_at", "") or ""))
        updated_at = parse_dt(str(item.get("updated_at", "") or ""))
    except Exception:
        return None
    if number <= 0 or not title:
        return None
    return Issue(
        number=number,
        title=title,
        state=state,
        created_at=created_at,
        updated_at=updated_at,
        labels=labels,
    )


def github_get_json(url: str, token: str) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "lab-safe-assistant-weekly-gate-ops",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8", errors="ignore")
    return json.loads(body)


def load_issues_from_github(repo: str, token: str) -> list[Issue]:
    owner, name = repo.split("/", 1)
    all_issues: list[Issue] = []
    per_page = 100
    for page in range(1, 11):
        qs = urllib.parse.urlencode(
            {
                "state": "all",
                "labels": "eval-gate-alert",
                "per_page": per_page,
                "page": page,
            }
        )
        url = f"https://api.github.com/repos/{owner}/{name}/issues?{qs}"
        payload = github_get_json(url, token=token)
        if not isinstance(payload, list):
            break
        page_items = 0
        for raw in payload:
            if isinstance(raw, dict):
                issue = parse_issue(raw)
                if issue is not None:
                    all_issues.append(issue)
                    page_items += 1
        if page_items < per_page:
            break
    return all_issues


def load_issues_from_json(path: Path) -> list[Issue]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("issues-json must be a JSON array")
    issues: list[Issue] = []
    for raw in payload:
        if isinstance(raw, dict):
            issue = parse_issue(raw)
            if issue is not None:
                issues.append(issue)
    return issues


def title_date(title: str) -> date | None:
    match = TITLE_DATE_PATTERN.match(title.strip())
    if not match:
        return None
    try:
        return date.fromisoformat(match.group(1))
    except ValueError:
        return None


def summarize(issues: list[Issue], *, start: date, end: date) -> dict[str, Any]:
    day_total = (end - start).days + 1
    by_day: dict[str, Issue] = {}
    for issue in issues:
        d = title_date(issue.title)
        if d is None or d < start or d > end:
            continue
        key = d.isoformat()
        prev = by_day.get(key)
        if prev is None or issue.updated_at > prev.updated_at:
            by_day[key] = issue

    fail_days = len(by_day)
    pass_days = max(0, day_total - fail_days)
    p1_days = sum(1 for issue in by_day.values() if "p1-gate" in issue.labels)
    open_alerts = sum(1 for issue in issues if issue.state == "open")
    open_p1 = sum(1 for issue in issues if issue.state == "open" and "p1-gate" in issue.labels)
    open_sla_missing = sum(
        1 for issue in issues if issue.state == "open" and "sla-missing" in issue.labels
    )

    rows = []
    current = start
    while current <= end:
        key = current.isoformat()
        issue = by_day.get(key)
        if issue is None:
            rows.append(
                {
                    "date": key,
                    "result": "PASS",
                    "issue_number": "",
                    "labels": "",
                }
            )
        else:
            labels = sorted(issue.labels)
            rows.append(
                {
                    "date": key,
                    "result": "FAIL",
                    "issue_number": f"#{issue.number}",
                    "labels": ",".join(labels),
                }
            )
        current += timedelta(days=1)

    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "days": day_total,
        "fail_days": fail_days,
        "pass_days": pass_days,
        "p1_days": p1_days,
        "open_alerts": open_alerts,
        "open_p1": open_p1,
        "open_sla_missing": open_sla_missing,
        "rows": rows,
    }


def render_markdown(summary: dict[str, Any], *, generated_at: str, source: str) -> str:
    lines: list[str] = []
    lines.append("# Weekly Gate Ops")
    lines.append("")
    lines.append(f"- Generated At: `{generated_at}`")
    lines.append(f"- Window: `{summary['start']}` to `{summary['end']}`")
    lines.append(f"- Source: `{source}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Window Days | {summary['days']} |")
    lines.append(f"| PASS Days | {summary['pass_days']} |")
    lines.append(f"| FAIL Days | {summary['fail_days']} |")
    lines.append(f"| P1 Days | {summary['p1_days']} |")
    lines.append(f"| Open Alerts | {summary['open_alerts']} |")
    lines.append(f"| Open P1 Alerts | {summary['open_p1']} |")
    lines.append(f"| Open SLA Missing | {summary['open_sla_missing']} |")
    lines.append("")
    lines.append("## Daily Breakdown")
    lines.append("")
    lines.append("| Date | Gate Result | Issue | Labels |")
    lines.append("|---|---|---|---|")
    for row in summary["rows"]:
        lines.append(
            f"| {row['date']} | {row['result']} | {row['issue_number']} | {row['labels']} |"
        )
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- `FAIL` is inferred from `eval-gate-alert` issue existence for that date.")
    lines.append("- `PASS` is inferred when no `eval-gate-alert` issue exists for that date in the window.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = repo_root / output_path

    today = date.fromisoformat(args.today) if args.today else datetime.now(timezone.utc).date()
    days = max(1, int(args.days))
    start = today - timedelta(days=days - 1)

    source = ""
    if args.issues_json:
        issues_path = Path(args.issues_json)
        if not issues_path.is_absolute():
            issues_path = repo_root / issues_path
        issues = load_issues_from_json(issues_path)
        source = f"issues-json:{issues_path}"
    else:
        repo = (args.repo or "").strip()
        token = (args.token or "").strip()
        if not repo or not token:
            raise SystemExit(
                "Missing repo/token. Provide --issues-json or set GITHUB_REPOSITORY + GITHUB_TOKEN."
            )
        issues = load_issues_from_github(repo=repo, token=token)
        source = f"github:{repo}"

    summary = summarize(issues, start=start, end=today)
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    markdown = render_markdown(summary, generated_at=generated_at, source=source)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")

    print(f"Generated weekly gate ops: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
