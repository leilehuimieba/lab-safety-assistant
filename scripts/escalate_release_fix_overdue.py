#!/usr/bin/env python3
"""
Escalate overdue P0 release-fix tasks by labeling and commenting linked GitHub issues.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


ACTIVE_STATUS = {"todo", "in_progress", "blocked"}
TASK_MARKER_PATTERN = re.compile(r"<!--\s*RELEASE_FIX_TASK:([^>]+)\s*-->")
DEFAULT_OVERDUE_LABEL = "release-fix-overdue"
DEFAULT_P1_LABEL = "p1-release-fix"


@dataclass
class OverdueTask:
    task_id: str
    issue_number: int
    issue_url: str
    owner: str
    status: str
    eta: str
    overdue_days: int
    reason: str


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Escalate overdue release fix tasks.")
    parser.add_argument("--repo-root", default=".", help="Repository root path.")
    parser.add_argument(
        "--fix-plan-csv",
        default="docs/ops/release_fix_plan_auto.csv",
        help="Release fix plan csv path.",
    )
    parser.add_argument(
        "--report-json",
        default="docs/ops/release_fix_overdue_report.json",
        help="Output json report path.",
    )
    parser.add_argument(
        "--report-md",
        default="docs/ops/release_fix_overdue_report.md",
        help="Output markdown report path.",
    )
    parser.add_argument(
        "--repo-slug",
        default="",
        help="GitHub repo slug owner/name. If empty, use env GITHUB_REPOSITORY.",
    )
    parser.add_argument(
        "--github-token",
        default="",
        help="GitHub token. If empty, use env GITHUB_TOKEN.",
    )
    parser.add_argument(
        "--priority",
        default="P0",
        help="Priority filter (default P0). Empty means all priorities.",
    )
    parser.add_argument(
        "--p1-threshold-days",
        type=int,
        default=3,
        help="Overdue day threshold to add p1 label.",
    )
    parser.add_argument(
        "--overdue-label",
        default=DEFAULT_OVERDUE_LABEL,
        help="Label added to overdue linked issues.",
    )
    parser.add_argument(
        "--p1-label",
        default=DEFAULT_P1_LABEL,
        help="Escalation label added when overdue days exceed threshold.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry-run only, no GitHub writes.",
    )
    parser.add_argument(
        "--today",
        default="",
        help="Override date in YYYY-MM-DD for testing.",
    )
    return parser.parse_args()


def resolve_path(repo_root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (repo_root / path).resolve()


def parse_date(value: str) -> date | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = [{str(k): str(v or "") for k, v in row.items()} for row in reader]
    return headers, rows


def marker_for_task(task_id: str) -> str:
    return f"<!-- RELEASE_FIX_TASK:{task_id} -->"


def marker_for_daily_comment(task_id: str, today: date) -> str:
    return f"<!-- RELEASE_FIX_OVERDUE:{task_id}:{today.isoformat()} -->"


def issue_task_id(issue: dict[str, Any]) -> str:
    body = str(issue.get("body", "") or "")
    match = TASK_MARKER_PATTERN.search(body)
    if not match:
        return ""
    return match.group(1).strip()


def collect_overdue_tasks(
    rows: list[dict[str, str]],
    *,
    today: date,
    priority_filter: str,
) -> list[OverdueTask]:
    target = str(priority_filter or "").strip().upper()
    result: list[OverdueTask] = []
    for row in rows:
        task_id = str(row.get("task_id", "")).strip()
        if not task_id:
            continue
        status = str(row.get("status", "")).strip().lower()
        if status not in ACTIVE_STATUS:
            continue
        priority = str(row.get("priority", "")).strip().upper()
        if target and priority != target:
            continue
        eta_raw = str(row.get("eta", "")).strip()
        eta = parse_date(eta_raw)
        if eta is None or eta >= today:
            continue
        overdue_days = (today - eta).days
        if overdue_days <= 0:
            continue
        issue_number_raw = str(row.get("issue_number", "")).strip()
        issue_number = int(issue_number_raw) if issue_number_raw.isdigit() else 0
        result.append(
            OverdueTask(
                task_id=task_id,
                issue_number=issue_number,
                issue_url=str(row.get("issue_url", "")).strip(),
                owner=str(row.get("owner", "")).strip(),
                status=status,
                eta=eta_raw,
                overdue_days=overdue_days,
                reason=str(row.get("blocking_reason", "")).strip(),
            )
        )
    return sorted(result, key=lambda x: (-x.overdue_days, x.task_id))


def build_overdue_comment(task: OverdueTask, *, today: date) -> str:
    marker = marker_for_daily_comment(task.task_id, today)
    return "\n".join(
        [
            marker,
            "Release fix task is overdue and requires follow-up.",
            "",
            f"- Task ID: `{task.task_id}`",
            f"- Status: `{task.status}`",
            f"- ETA: `{task.eta}`",
            f"- Overdue Days: `{task.overdue_days}`",
            f"- Owner: `{task.owner or '(empty)'}`",
            "",
            "Please update owner/eta/status and post remediation progress.",
        ]
    )


class GitHubClient:
    def __init__(self, *, token: str, repo_slug: str):
        self.token = token
        self.repo_slug = repo_slug
        self.base = "https://api.github.com"

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        url = f"{self.base}{path}"
        body = None
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "lab-safe-assistant-release-fix-overdue",
        }
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url=url, method=method, headers=headers, data=body)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                text = resp.read().decode("utf-8", errors="replace")
                return json.loads(text) if text else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"GitHub API {method} {path} failed: {exc.code} {detail}") from exc

    def list_release_fix_issues(self, state: str = "all") -> list[dict[str, Any]]:
        query = urllib.parse.urlencode({"state": state, "labels": "release-fix-task", "per_page": "100"})
        data = self._request("GET", f"/repos/{self.repo_slug}/issues?{query}")
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        return []

    def update_issue(self, issue_number: int, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._request("PATCH", f"/repos/{self.repo_slug}/issues/{issue_number}", payload=payload)
        return data if isinstance(data, dict) else {}

    def list_comments(self, issue_number: int) -> list[dict[str, Any]]:
        query = urllib.parse.urlencode({"per_page": "100"})
        data = self._request("GET", f"/repos/{self.repo_slug}/issues/{issue_number}/comments?{query}")
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        return []

    def create_comment(self, issue_number: int, body: str) -> dict[str, Any]:
        data = self._request("POST", f"/repos/{self.repo_slug}/issues/{issue_number}/comments", {"body": body})
        return data if isinstance(data, dict) else {}


def index_issues(issues: list[dict[str, Any]]) -> tuple[dict[int, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_number: dict[int, dict[str, Any]] = {}
    by_task: dict[str, dict[str, Any]] = {}
    for issue in issues:
        number = int(issue.get("number", 0) or 0)
        if number > 0:
            by_number[number] = issue
        task_id = issue_task_id(issue)
        if task_id:
            by_task[task_id] = issue
    return by_number, by_task


def labels_union(current: list[str], required: list[str]) -> list[str]:
    result = list(current)
    existing = {item for item in current}
    for item in required:
        if item and item not in existing:
            result.append(item)
            existing.add(item)
    return result


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    csv_path = resolve_path(repo_root, args.fix_plan_csv)
    report_json = resolve_path(repo_root, args.report_json)
    report_md = resolve_path(repo_root, args.report_md)
    today = date.fromisoformat(args.today) if args.today else datetime.now(timezone.utc).date()

    if not csv_path.exists():
        print(f"release fix overdue escalation failed: missing csv: {csv_path}")
        return 1

    _headers, rows = read_csv(csv_path)
    overdue_tasks = collect_overdue_tasks(rows, today=today, priority_filter=args.priority)

    repo_slug = str(args.repo_slug or "").strip() or str(os.environ.get("GITHUB_REPOSITORY", "")).strip()
    token = str(args.github_token or "").strip() or str(os.environ.get("GITHUB_TOKEN", "")).strip()
    dry_run = bool(args.dry_run)
    if not repo_slug:
        print("release fix overdue escalation failed: missing repo slug")
        return 1
    if not token and not dry_run:
        print("release fix overdue escalation failed: missing token")
        return 1

    client = GitHubClient(token=token, repo_slug=repo_slug) if not dry_run else None
    issues = client.list_release_fix_issues(state="all") if client else []
    by_number, by_task = index_issues(issues)

    notified = 0
    label_updated = 0
    p1_escalated = 0
    skipped_no_issue = 0
    skipped_closed = 0
    skipped_duplicate_daily_comment = 0
    errors: list[str] = []
    touched: list[str] = []

    for task in overdue_tasks:
        issue = by_number.get(task.issue_number) if task.issue_number > 0 else None
        if issue is None:
            issue = by_task.get(task.task_id)
        if issue is None:
            skipped_no_issue += 1
            continue
        issue_number = int(issue.get("number", 0) or 0)
        issue_state = str(issue.get("state", "")).strip().lower()
        if issue_number <= 0:
            skipped_no_issue += 1
            continue
        if issue_state == "closed":
            skipped_closed += 1
            continue

        try:
            labels_raw = issue.get("labels", [])
            current_labels: list[str] = []
            if isinstance(labels_raw, list):
                for item in labels_raw:
                    if isinstance(item, dict):
                        name = str(item.get("name", "")).strip()
                        if name:
                            current_labels.append(name)
                    elif isinstance(item, str):
                        name = item.strip()
                        if name:
                            current_labels.append(name)

            required_labels = [args.overdue_label]
            if task.overdue_days >= max(1, int(args.p1_threshold_days)):
                required_labels.append(args.p1_label)
            merged_labels = labels_union(current_labels, required_labels)

            if merged_labels != current_labels:
                label_updated += 1
                if task.overdue_days >= max(1, int(args.p1_threshold_days)):
                    p1_escalated += 1
                if not dry_run and client:
                    issue = client.update_issue(issue_number, {"labels": merged_labels})

            today_marker = marker_for_daily_comment(task.task_id, today)
            has_today_comment = False
            if not dry_run and client:
                comments = client.list_comments(issue_number)
                has_today_comment = any(today_marker in str(c.get("body", "") or "") for c in comments)

            if has_today_comment:
                skipped_duplicate_daily_comment += 1
                touched.append(task.task_id)
                continue

            comment_body = build_overdue_comment(task, today=today)
            if not dry_run and client:
                client.create_comment(issue_number, comment_body)
            notified += 1
            touched.append(task.task_id)
        except Exception as exc:
            errors.append(f"{task.task_id}: {exc}")

    report = {
        "generated_at": now_iso(),
        "repo_slug": repo_slug,
        "dry_run": dry_run,
        "today": today.isoformat(),
        "priority_filter": str(args.priority or ""),
        "overdue_count": len(overdue_tasks),
        "counts": {
            "notified": notified,
            "label_updated": label_updated,
            "p1_escalated": p1_escalated,
            "skipped_no_issue": skipped_no_issue,
            "skipped_closed": skipped_closed,
            "skipped_duplicate_daily_comment": skipped_duplicate_daily_comment,
            "errors": len(errors),
        },
        "touched_tasks": touched,
        "errors": errors,
        "overdue_tasks": [task.__dict__ for task in overdue_tasks],
    }
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Release Fix Overdue Escalation Report",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Repo: `{repo_slug}`",
        f"- Dry Run: `{dry_run}`",
        f"- Today: `{today.isoformat()}`",
        f"- Priority Filter: `{report['priority_filter']}`",
        f"- Overdue Tasks: `{len(overdue_tasks)}`",
        "",
        "## Counts",
        f"- notified: `{notified}`",
        f"- label_updated: `{label_updated}`",
        f"- p1_escalated: `{p1_escalated}`",
        f"- skipped_no_issue: `{skipped_no_issue}`",
        f"- skipped_closed: `{skipped_closed}`",
        f"- skipped_duplicate_daily_comment: `{skipped_duplicate_daily_comment}`",
        f"- errors: `{len(errors)}`",
        "",
        "## Touched Tasks",
    ]
    if touched:
        lines.extend([f"- `{item}`" for item in touched])
    else:
        lines.append("- none")
    if errors:
        lines.extend(["", "## Errors"])
        lines.extend([f"- {item}" for item in errors])
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"release fix overdue report: {report_json}")
    print(f"release fix overdue markdown: {report_md}")
    print(
        "overdue escalation counts: "
        f"notified={notified}, p1_escalated={p1_escalated}, errors={len(errors)}"
    )
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
