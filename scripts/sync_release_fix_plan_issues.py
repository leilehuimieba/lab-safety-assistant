#!/usr/bin/env python3
"""
Sync release fix plan tasks to GitHub issues.
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_LABELS = ["release-fix-task"]
ACTIVE_STATUS = {"todo", "in_progress", "blocked"}
CLOSED_STATUS = {"done", "wont_fix"}


@dataclass
class OwnerParseResult:
    valid: list[str]
    invalid: list[str]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync release fix plan rows to GitHub issues.")
    parser.add_argument("--repo-root", default=".", help="Repository root path.")
    parser.add_argument(
        "--fix-plan-csv",
        default="docs/ops/release_fix_plan_auto.csv",
        help="Release fix plan csv path.",
    )
    parser.add_argument(
        "--report-json",
        default="docs/ops/release_fix_plan_sync_report.json",
        help="Sync report json output path.",
    )
    parser.add_argument(
        "--report-md",
        default="docs/ops/release_fix_plan_sync_report.md",
        help="Sync report markdown output path.",
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
        "--only-priority",
        default="P0",
        help="Only sync rows matching this priority (empty means all).",
    )
    parser.add_argument(
        "--assign-from-owner",
        action="store_true",
        help="Try assigning issue to owner field (GitHub usernames).",
    )
    parser.add_argument(
        "--close-on-done",
        action="store_true",
        default=True,
        help="Close linked issue when task status is done/wont_fix.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Dry-run only, no GitHub API writes.")
    parser.add_argument("--quiet", action="store_true", help="Print concise output.")
    return parser.parse_args()


def resolve_path(repo_root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (repo_root / path).resolve()


def marker_for_task(task_id: str) -> str:
    return f"<!-- RELEASE_FIX_TASK:{task_id} -->"


def short_text(text: str, limit: int = 80) -> str:
    compact = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(compact) <= limit:
        return compact
    return compact[: max(0, limit - 3)] + "..."


def build_issue_title(task_id: str, reason: str) -> str:
    reason_part = short_text(reason, limit=70)
    return f"[Release Fix] {task_id} {reason_part}".strip()


def parse_owner_field(owner: str) -> OwnerParseResult:
    raw = str(owner or "").strip()
    if not raw:
        return OwnerParseResult(valid=[], invalid=[])
    tokens = re.split(r"[,\s;]+", raw)
    valid: list[str] = []
    invalid: list[str] = []
    for token in tokens:
        candidate = token.strip().lstrip("@")
        if not candidate:
            continue
        if re.fullmatch(r"[A-Za-z0-9-]+", candidate):
            valid.append(candidate)
        else:
            invalid.append(candidate)
    return OwnerParseResult(valid=sorted(set(valid)), invalid=sorted(set(invalid)))


def parse_owner_to_assignees(owner: str) -> list[str]:
    return parse_owner_field(owner).valid


def is_assignee_error(exc: Exception) -> bool:
    text = str(exc or "").lower()
    return "assignee" in text or "could not resolve to a user" in text


def build_issue_body(row: dict[str, str]) -> str:
    task_id = str(row.get("task_id", "")).strip()
    priority = str(row.get("priority", "")).strip()
    status = str(row.get("status", "")).strip()
    owner = str(row.get("owner", "")).strip()
    eta = str(row.get("eta", "")).strip()
    profiles = str(row.get("profiles", "")).strip()
    reason = str(row.get("blocking_reason", "")).strip()
    action = str(row.get("recommended_action", "")).strip()
    verify = str(row.get("verification_step", "")).strip()
    marker = marker_for_task(task_id)
    return "\n".join(
        [
            marker,
            "Auto-synced release fix task from `docs/ops/release_fix_plan_auto.csv`.",
            "",
            f"- Task ID: `{task_id}`",
            f"- Priority: `{priority}`",
            f"- Status: `{status}`",
            f"- Owner: `{owner}`",
            f"- ETA: `{eta}`",
            f"- Profiles: `{profiles}`",
            "",
            "## Blocking Reason",
            reason or "(empty)",
            "",
            "## Recommended Action",
            action or "(empty)",
            "",
            "## Verification Step",
            verify or "(empty)",
            "",
            "Update issue body/comments and the source CSV together when status changes.",
        ]
    )


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = [{str(k): str(v or "") for k, v in row.items()} for row in reader]
    return headers, rows


def write_csv(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in headers})


def ensure_headers(headers: list[str], required: list[str]) -> list[str]:
    out = list(headers)
    for item in required:
        if item not in out:
            out.append(item)
    return out


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
            "User-Agent": "lab-safe-assistant-release-fix-sync",
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

    def list_task_issues(self) -> list[dict[str, Any]]:
        query = urllib.parse.urlencode(
            {
                "state": "all",
                "labels": ",".join(DEFAULT_LABELS),
                "per_page": "100",
            }
        )
        data = self._request("GET", f"/repos/{self.repo_slug}/issues?{query}")
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        return []

    def create_issue(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._request("POST", f"/repos/{self.repo_slug}/issues", payload=payload)
        return data if isinstance(data, dict) else {}

    def update_issue(self, issue_number: int, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._request("PATCH", f"/repos/{self.repo_slug}/issues/{issue_number}", payload=payload)
        return data if isinstance(data, dict) else {}


def index_issues_by_task(issues: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    pattern = re.compile(r"<!--\s*RELEASE_FIX_TASK:([^>]+)\s*-->")
    for issue in issues:
        body = str(issue.get("body", "") or "")
        match = pattern.search(body)
        if not match:
            continue
        task_id = match.group(1).strip()
        if task_id:
            result[task_id] = issue
    return result


def status_norm(value: str) -> str:
    return str(value or "").strip().lower()


def priority_match(value: str, target: str) -> bool:
    if not str(target or "").strip():
        return True
    return str(value or "").strip().upper() == str(target or "").strip().upper()


def upsert_row_sync_meta(row: dict[str, str], *, issue: dict[str, Any] | None) -> None:
    if issue is None:
        return
    row["issue_number"] = str(issue.get("number", "") or "")
    row["issue_url"] = str(issue.get("html_url", "") or "")
    row["last_synced_at"] = now_iso()


def upsert_issue_with_assignee_fallback(
    *,
    client: GitHubClient,
    existing: dict[str, Any] | None,
    payload: dict[str, Any],
    assignees: list[str],
    task_id: str,
    warnings: list[str],
) -> tuple[dict[str, Any], bool]:
    try:
        if existing is None:
            issue = client.create_issue(payload)
        else:
            issue_number = int(existing.get("number", 0) or 0)
            issue = client.update_issue(issue_number, payload)
        return issue, False
    except Exception as exc:
        if not assignees or not is_assignee_error(exc):
            raise
        fallback_payload = dict(payload)
        fallback_payload.pop("assignees", None)
        warnings.append(
            f"{task_id}: assignee fallback applied (owner not assignable): {', '.join(assignees)}"
        )
        if existing is None:
            issue = client.create_issue(fallback_payload)
        else:
            issue_number = int(existing.get("number", 0) or 0)
            issue = client.update_issue(issue_number, fallback_payload)
        return issue, True


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    csv_path = resolve_path(repo_root, args.fix_plan_csv)
    report_json = resolve_path(repo_root, args.report_json)
    report_md = resolve_path(repo_root, args.report_md)

    if not csv_path.exists():
        print(f"release fix issue sync failed: missing csv: {csv_path}")
        return 1

    headers, rows = read_csv(csv_path)
    headers = ensure_headers(headers, ["issue_number", "issue_url", "last_synced_at"])

    repo_slug = str(args.repo_slug or "").strip() or str(os.environ.get("GITHUB_REPOSITORY", "")).strip()
    token = str(args.github_token or "").strip() or str(os.environ.get("GITHUB_TOKEN", "")).strip()
    dry_run = bool(args.dry_run)
    if not repo_slug:
        print("release fix issue sync failed: missing repo slug (use --repo-slug or GITHUB_REPOSITORY)")
        return 1
    if not token and not dry_run:
        print("release fix issue sync failed: missing token (use --github-token or GITHUB_TOKEN, or --dry-run)")
        return 1

    client = GitHubClient(token=token, repo_slug=repo_slug) if not dry_run else None
    existing_issues = client.list_task_issues() if client else []
    issues_by_task = index_issues_by_task(existing_issues)

    created = 0
    updated = 0
    closed = 0
    skipped = 0
    warning_count_owner_parse = 0
    warning_count_owner_empty = 0
    warning_count_assignee_fallback = 0
    warnings: list[str] = []
    errors: list[str] = []
    touched_tasks: list[str] = []

    for row in rows:
        task_id = str(row.get("task_id", "")).strip()
        priority = str(row.get("priority", "")).strip().upper()
        status = status_norm(row.get("status", ""))
        if not task_id:
            skipped += 1
            continue
        if not priority_match(priority, args.only_priority):
            skipped += 1
            continue

        existing = issues_by_task.get(task_id)
        title = build_issue_title(task_id, str(row.get("blocking_reason", "")))
        body = build_issue_body(row)
        owner_raw = str(row.get("owner", "")).strip()
        assignees: list[str] = []
        if args.assign_from_owner:
            owner_parsed = parse_owner_field(owner_raw)
            assignees = owner_parsed.valid
            if owner_parsed.invalid:
                warning_count_owner_parse += 1
                warnings.append(
                    f"{task_id}: invalid owner tokens skipped: {', '.join(owner_parsed.invalid)}"
                )
            if owner_raw and not assignees:
                warning_count_owner_empty += 1
                warnings.append(
                    f"{task_id}: owner present but no valid assignee parsed, continue without assignee"
                )

        try:
            if status in ACTIVE_STATUS:
                payload: dict[str, Any] = {
                    "title": title,
                    "body": body,
                    "labels": DEFAULT_LABELS + [f"priority-{priority.lower()}"],
                    "state": "open",
                }
                if assignees:
                    payload["assignees"] = assignees

                if existing is None:
                    if dry_run:
                        fake = {"number": "", "html_url": "", "state": "open"}
                        upsert_row_sync_meta(row, issue=fake)
                    else:
                        issue = {}
                        used_fallback = False
                        if client:
                            issue, used_fallback = upsert_issue_with_assignee_fallback(
                                client=client,
                                existing=None,
                                payload=payload,
                                assignees=assignees,
                                task_id=task_id,
                                warnings=warnings,
                            )
                        if used_fallback:
                            warning_count_assignee_fallback += 1
                        upsert_row_sync_meta(row, issue=issue)
                        issues_by_task[task_id] = issue
                    created += 1
                    touched_tasks.append(task_id)
                else:
                    issue_number = int(existing.get("number", 0) or 0)
                    if issue_number > 0 and not dry_run and client:
                        issue, used_fallback = upsert_issue_with_assignee_fallback(
                            client=client,
                            existing=existing,
                            payload=payload,
                            assignees=assignees,
                            task_id=task_id,
                            warnings=warnings,
                        )
                        if used_fallback:
                            warning_count_assignee_fallback += 1
                        upsert_row_sync_meta(row, issue=issue)
                        issues_by_task[task_id] = issue
                    else:
                        upsert_row_sync_meta(row, issue=existing)
                    updated += 1
                    touched_tasks.append(task_id)

            elif status in CLOSED_STATUS:
                if existing is not None:
                    issue_number = int(existing.get("number", 0) or 0)
                    issue_state = str(existing.get("state", "") or "").strip().lower()
                    if issue_number > 0 and issue_state != "closed" and args.close_on_done:
                        if not dry_run and client:
                            issue = client.update_issue(issue_number, {"state": "closed"})
                            upsert_row_sync_meta(row, issue=issue)
                            issues_by_task[task_id] = issue
                        else:
                            upsert_row_sync_meta(row, issue=existing)
                        closed += 1
                        touched_tasks.append(task_id)
                    else:
                        upsert_row_sync_meta(row, issue=existing)
                        skipped += 1
                else:
                    skipped += 1
            else:
                skipped += 1
        except Exception as exc:
            errors.append(f"{task_id}: {exc}")

    if not dry_run:
        write_csv(csv_path, headers, rows)

    report = {
        "generated_at": now_iso(),
        "repo_slug": repo_slug,
        "fix_plan_csv": str(csv_path),
        "dry_run": dry_run,
        "only_priority": str(args.only_priority or ""),
        "counts": {
            "total_rows": len(rows),
            "created": created,
            "updated": updated,
            "closed": closed,
            "skipped": skipped,
            "errors": len(errors),
            "warnings": len(warnings),
            "owner_parse_warnings": warning_count_owner_parse,
            "owner_no_valid_assignee": warning_count_owner_empty,
            "assignee_fallbacks": warning_count_assignee_fallback,
        },
        "touched_tasks": touched_tasks,
        "warnings": warnings,
        "errors": errors,
    }

    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Release Fix Plan Sync Report",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Repo: `{repo_slug}`",
        f"- Dry Run: `{dry_run}`",
        f"- Priority Filter: `{report['only_priority']}`",
        "",
        "## Counts",
        f"- total_rows: `{report['counts']['total_rows']}`",
        f"- created: `{created}`",
        f"- updated: `{updated}`",
        f"- closed: `{closed}`",
        f"- skipped: `{skipped}`",
        f"- warnings: `{len(warnings)}`",
        f"- owner_parse_warnings: `{warning_count_owner_parse}`",
        f"- owner_no_valid_assignee: `{warning_count_owner_empty}`",
        f"- assignee_fallbacks: `{warning_count_assignee_fallback}`",
        f"- errors: `{len(errors)}`",
        "",
        "## Touched Tasks",
    ]
    if touched_tasks:
        lines.extend([f"- `{task}`" for task in touched_tasks])
    else:
        lines.append("- none")
    if errors:
        lines.extend(["", "## Errors"])
        lines.extend([f"- {item}" for item in errors])
    if warnings:
        lines.extend(["", "## Warnings"])
        lines.extend([f"- {item}" for item in warnings])
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if not args.quiet:
        print(f"release fix sync report: {report_json}")
        print(f"release fix sync markdown: {report_md}")
        print(
            "sync counts: "
            f"created={created}, updated={updated}, closed={closed}, skipped={skipped}, errors={len(errors)}"
        )

    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
