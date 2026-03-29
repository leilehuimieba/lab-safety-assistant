#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import random
import string
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_FIELDS = [
    "title",
    "category",
    "subcategory",
    "lab_type",
    "risk_level",
    "hazard_types",
    "scenario",
    "question",
    "answer",
    "steps",
    "ppe",
    "forbidden",
    "disposal",
    "first_aid",
    "emergency",
    "legal_notes",
    "references",
    "source_type",
    "source_title",
    "source_org",
    "source_version",
    "source_date",
    "source_url",
    "tags",
    "language",
]


@dataclass
class ImportResult:
    created: int = 0
    skipped_existing: int = 0
    failed: int = 0
    batches: list[str] | None = None


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import knowledge_base_import_ready.csv to Dify Dataset via service API."
    )
    parser.add_argument(
        "--csv",
        default="release_exports/v7/knowledge_base_import_ready.csv",
        help="Input CSV path.",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8080",
        help="Dify base URL, e.g. http://localhost:8080",
    )
    parser.add_argument(
        "--dataset-id",
        default="",
        help="Target dataset id. If empty and --auto-detect-dataset is enabled, auto select from DB.",
    )
    parser.add_argument(
        "--dataset-api-key",
        default="",
        help="Dataset API token. If empty and --auto-provision-token is enabled, a dataset token is generated via DB.",
    )
    parser.add_argument(
        "--db-container",
        default="docker-db_postgres-1",
        help="Postgres container name used for auto-detect/provision.",
    )
    parser.add_argument("--db-user", default="postgres", help="Postgres user.")
    parser.add_argument("--db-name", default="dify", help="Postgres database name.")
    parser.add_argument(
        "--dataset-name",
        default="实验室安全知识库",
        help="Dataset name used by --auto-detect-dataset.",
    )
    parser.add_argument(
        "--auto-detect-dataset",
        action="store_true",
        help="Auto detect dataset id by dataset name from Postgres.",
    )
    parser.add_argument(
        "--auto-provision-token",
        action="store_true",
        help="Auto create a dataset API token in Postgres when dataset-api-key is not provided.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip rows when a document with same generated name already exists.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Only import first N rows (0 means all).",
    )
    parser.add_argument(
        "--sleep-ms",
        type=int,
        default=0,
        help="Sleep milliseconds between create calls.",
    )
    parser.add_argument(
        "--wait-indexing",
        action="store_true",
        help="Poll indexing status for created batches until completed/paused/error.",
    )
    parser.add_argument(
        "--wait-timeout-sec",
        type=int,
        default=1800,
        help="Total wait timeout in seconds for --wait-indexing.",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/dify_import_v7/import_report.json",
        help="Output json report path.",
    )
    parser.add_argument(
        "--report-md",
        default="docs/eval/dify_import_v7_report.md",
        help="Output markdown report path.",
    )
    return parser.parse_args()


def _url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}{path}"


def request_json(
    method: str,
    url: str,
    *,
    token: str,
    payload: dict[str, Any] | None = None,
    timeout: float = 60.0,
) -> tuple[int, dict[str, Any]]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = b""
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body if method != "GET" else None, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
            if not raw.strip():
                return resp.status, {}
            return resp.status, json.loads(raw)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="ignore")
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"message": raw}
        return exc.code, payload


def run_psql_sql(
    *,
    container: str,
    db_user: str,
    db_name: str,
    sql: str,
) -> str:
    cmd = [
        "docker",
        "exec",
        container,
        "psql",
        "-U",
        db_user,
        "-d",
        db_name,
        "-t",
        "-A",
        "-c",
        sql,
    ]
    completed = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout).strip())
    return completed.stdout.strip()


def auto_detect_dataset_id(args: argparse.Namespace) -> str:
    dataset_name_sql = args.dataset_name.replace("'", "''")
    sql = (
        "select id from datasets "
        f"where name='{dataset_name_sql}' "
        "order by created_at desc limit 1;"
    )
    dataset_id = run_psql_sql(
        container=args.db_container,
        db_user=args.db_user,
        db_name=args.db_name,
        sql=sql,
    ).strip()
    if not dataset_id:
        # Fallback for terminal encoding issues on non-UTF8 shells.
        fallback_sql = "select id from datasets order by created_at desc limit 1;"
        dataset_id = run_psql_sql(
            container=args.db_container,
            db_user=args.db_user,
            db_name=args.db_name,
            sql=fallback_sql,
        ).strip()
        if dataset_id:
            print(
                f"[warn] dataset name match failed for '{args.dataset_name}', fallback to latest dataset id: {dataset_id}"
            )
    if not dataset_id:
        raise RuntimeError("Cannot auto-detect dataset id from database.")
    return dataset_id


def auto_provision_dataset_token(args: argparse.Namespace, dataset_id: str) -> str:
    tenant_sql = (
        "select tenant_id from datasets "
        f"where id='{dataset_id}' "
        "limit 1;"
    )
    tenant_id = run_psql_sql(
        container=args.db_container,
        db_user=args.db_user,
        db_name=args.db_name,
        sql=tenant_sql,
    ).strip()
    if not tenant_id:
        raise RuntimeError(f"Cannot resolve tenant_id for dataset: {dataset_id}")

    suffix = "".join(random.choice(string.ascii_letters + string.digits) for _ in range(32))
    token = f"dataset-{suffix}"
    insert_sql = (
        "insert into api_tokens(id,app_id,tenant_id,type,token,created_at) "
        f"values (uuid_generate_v4(), NULL, '{tenant_id}', 'dataset', '{token}', now()) "
        "returning token;"
    )
    created_raw = run_psql_sql(
        container=args.db_container,
        db_user=args.db_user,
        db_name=args.db_name,
        sql=insert_sql,
    )
    created = ""
    for line in created_raw.splitlines():
        item = line.strip()
        if item.startswith("dataset-"):
            created = item
            break
    if not created:
        raise RuntimeError("Failed to auto-provision dataset token.")
    return created


def read_rows(path: Path, limit: int = 0) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if limit > 0:
        return rows[:limit]
    return rows


def build_doc_name(row: dict[str, str]) -> str:
    raw = f"{(row.get('id') or '').strip()} {(row.get('title') or '').strip()}".strip()
    if not raw:
        raw = f"kb-{int(time.time() * 1000)}"
    # Keep the name short for easier list/lookup.
    return raw[:180]


def build_doc_text(row: dict[str, str]) -> str:
    lines: list[str] = []
    row_id = (row.get("id") or "").strip()
    if row_id:
        lines.append(f"id: {row_id}")
    for field in DEFAULT_FIELDS:
        value = (row.get(field) or "").strip()
        if value:
            lines.append(f"{field}: {value}")
    return "\n".join(lines).strip()


def list_existing_names(base_url: str, dataset_id: str, token: str) -> set[str]:
    names: set[str] = set()
    page = 1
    limit = 100
    while True:
        params = urllib.parse.urlencode({"page": page, "limit": limit})
        url = _url(base_url, f"/v1/datasets/{dataset_id}/documents?{params}")
        status, payload = request_json("GET", url, token=token, payload=None, timeout=30.0)
        if status != 200:
            break
        data = payload.get("data") or []
        if not isinstance(data, list) or not data:
            break
        for item in data:
            if isinstance(item, dict):
                name = str(item.get("name") or "").strip()
                if name:
                    names.add(name)
        has_more = bool(payload.get("has_more"))
        if not has_more:
            break
        page += 1
    return names


def create_document(base_url: str, dataset_id: str, token: str, *, name: str, text: str) -> tuple[int, dict[str, Any]]:
    payload = {
        "name": name,
        "text": text,
        "indexing_technique": "high_quality",
        "process_rule": {"mode": "automatic"},
    }
    url = _url(base_url, f"/v1/datasets/{dataset_id}/document/create-by-text")
    status, result = request_json("POST", url, token=token, payload=payload, timeout=60.0)
    if status == 404:
        # Compatibility for old endpoint naming.
        url = _url(base_url, f"/v1/datasets/{dataset_id}/document/create_by_text")
        status, result = request_json("POST", url, token=token, payload=payload, timeout=60.0)
    return status, result


def poll_batch_indexing(
    base_url: str,
    dataset_id: str,
    token: str,
    batches: list[str],
    timeout_sec: int,
) -> dict[str, str]:
    deadline = time.time() + max(timeout_sec, 30)
    pending = {item: "unknown" for item in batches}
    while pending and time.time() < deadline:
        finished: list[str] = []
        for batch in list(pending.keys()):
            url = _url(base_url, f"/v1/datasets/{dataset_id}/documents/{batch}/indexing-status")
            status, payload = request_json("GET", url, token=token, payload=None, timeout=30.0)
            if status != 200:
                continue
            data = payload.get("data") or []
            statuses: list[str] = []
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        statuses.append(str(item.get("indexing_status") or "").strip().lower())
            if not statuses:
                continue
            if all(s in {"completed", "paused", "error", "stopped"} for s in statuses):
                # Keep worst-case state when mixed.
                final = "completed"
                if any(s == "error" for s in statuses):
                    final = "error"
                elif any(s == "paused" for s in statuses):
                    final = "paused"
                elif any(s == "stopped" for s in statuses):
                    final = "stopped"
                pending[batch] = final
                finished.append(batch)
        for batch in finished:
            pending.pop(batch, None)
        if pending:
            time.sleep(2.0)
    for key in list(pending.keys()):
        pending[key] = "timeout"
    return pending


def write_report(
    *,
    result: ImportResult,
    csv_path: Path,
    base_url: str,
    dataset_id: str,
    report_json: Path,
    report_md: Path,
    wait_pending: dict[str, str] | None,
) -> None:
    payload = {
        "generated_at": now_iso(),
        "csv_path": str(csv_path),
        "base_url": base_url,
        "dataset_id": dataset_id,
        "created": result.created,
        "skipped_existing": result.skipped_existing,
        "failed": result.failed,
        "batches_count": len(result.batches or []),
        "wait_pending": wait_pending or {},
    }
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Dify Dataset Import Report",
        "",
        f"- generated_at: `{payload['generated_at']}`",
        f"- csv_path: `{csv_path}`",
        f"- base_url: `{base_url}`",
        f"- dataset_id: `{dataset_id}`",
        f"- created: `{result.created}`",
        f"- skipped_existing: `{result.skipped_existing}`",
        f"- failed: `{result.failed}`",
        f"- batches_count: `{len(result.batches or [])}`",
    ]
    if wait_pending:
        lines.extend(
            [
                "",
                "## Wait Indexing Pending/Timeout",
                "",
                "| batch | state |",
                "|---|---|",
            ]
        )
        for batch, state in sorted(wait_pending.items()):
            lines.append(f"| {batch} | {state} |")

    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    csv_path = Path(args.csv).resolve()
    report_json = Path(args.report_json).resolve()
    report_md = Path(args.report_md).resolve()

    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}")

    dataset_id = args.dataset_id.strip()
    if not dataset_id and args.auto_detect_dataset:
        dataset_id = auto_detect_dataset_id(args)
        print(f"[info] auto-detected dataset_id: {dataset_id}")
    if not dataset_id:
        raise SystemExit("Missing dataset id. Provide --dataset-id or enable --auto-detect-dataset.")

    token = args.dataset_api_key.strip()
    if not token and args.auto_provision_token:
        token = auto_provision_dataset_token(args, dataset_id)
        print(f"[info] auto-provisioned dataset token: {token[:16]}***")
    if not token:
        raise SystemExit("Missing dataset API key. Provide --dataset-api-key or enable --auto-provision-token.")

    rows = read_rows(csv_path, args.limit)
    existing_names: set[str] = set()
    if args.skip_existing:
        existing_names = list_existing_names(args.base_url, dataset_id, token)
        print(f"[info] existing document names loaded: {len(existing_names)}")

    result = ImportResult(created=0, skipped_existing=0, failed=0, batches=[])

    for idx, row in enumerate(rows, start=1):
        name = build_doc_name(row)
        if args.skip_existing and name in existing_names:
            result.skipped_existing += 1
            continue

        text = build_doc_text(row)
        if not text:
            result.failed += 1
            print(f"[warn] empty text row skipped at #{idx}")
            continue

        status, payload = create_document(args.base_url, dataset_id, token, name=name, text=text)
        if status == 200:
            result.created += 1
            batch = str(payload.get("batch") or "").strip()
            if batch:
                result.batches.append(batch)
            if args.skip_existing:
                existing_names.add(name)
        else:
            result.failed += 1
            msg = str(payload.get("message") or payload.get("code") or payload)
            print(f"[warn] create failed #{idx} status={status} name={name[:48]} msg={msg}")

        if args.sleep_ms > 0:
            time.sleep(max(0, args.sleep_ms) / 1000.0)

    wait_pending: dict[str, str] | None = None
    if args.wait_indexing and result.batches:
        unique_batches = sorted(set(result.batches))
        wait_pending = poll_batch_indexing(
            args.base_url,
            dataset_id,
            token,
            batches=unique_batches,
            timeout_sec=args.wait_timeout_sec,
        )

    write_report(
        result=result,
        csv_path=csv_path,
        base_url=args.base_url,
        dataset_id=dataset_id,
        report_json=report_json,
        report_md=report_md,
        wait_pending=wait_pending,
    )

    print("[done] dataset import completed")
    print(f"- csv: {csv_path}")
    print(f"- created: {result.created}")
    print(f"- skipped_existing: {result.skipped_existing}")
    print(f"- failed: {result.failed}")
    print(f"- report_json: {report_json}")
    print(f"- report_md: {report_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
