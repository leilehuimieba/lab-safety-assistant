#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import requests


DEFAULT_API_BASE = "http://127.0.0.1:8080"
DEFAULT_QUERY = "实验室发生化学品泄漏时，第一步应该做什么？"


@dataclass
class SmokeResult:
    http_status: int
    workflow_status: Optional[str]
    workflow_run_id: Optional[str]
    answer: str
    error_message: Optional[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one real Dify business smoke request.")
    parser.add_argument("--api-base", default=DEFAULT_API_BASE, help="Dify base URL.")
    parser.add_argument("--app-token", required=True, help="Dify app token.")
    parser.add_argument("--query", default=DEFAULT_QUERY, help="Business smoke query.")
    parser.add_argument("--user", default="server-business-smoke", help="Dify user id.")
    parser.add_argument("--timeout-sec", type=int, default=120, help="Read timeout seconds.")
    parser.add_argument("--output-json", default="", help="Optional output json path.")
    return parser.parse_args()


def run_workflow_smoke(
    *,
    base_url: str,
    app_token: str,
    query: str,
    user: str,
    timeout_sec: int,
) -> SmokeResult:
    headers = {
        "Authorization": f"Bearer {app_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "inputs": {},
        "query": query,
        "response_mode": "streaming",
        "user": user,
    }

    response = requests.post(
        f"{base_url.rstrip('/')}/v1/chat-messages",
        headers=headers,
        json=payload,
        timeout=(20, timeout_sec),
        stream=True,
    )

    answer_parts: list[str] = []
    workflow_status = None
    workflow_run_id = None
    error_message = None

    if response.status_code != 200:
        return SmokeResult(
            http_status=response.status_code,
            workflow_status=None,
            workflow_run_id=None,
            answer="",
            error_message=f"http {response.status_code}: {response.text[:500]}",
        )

    for raw in response.iter_lines(decode_unicode=True):
        if not raw:
            continue
        line = raw.strip()
        if not line.startswith("data: "):
            continue

        try:
            obj = json.loads(line[6:])
        except Exception:
            continue

        event = obj.get("event")
        if event == "message":
            chunk = str(obj.get("answer") or "").strip()
            if chunk:
                answer_parts.append(chunk)
        elif event == "workflow_finished":
            data = obj.get("data") or {}
            workflow_status = data.get("status")
            workflow_run_id = data.get("id")
            break
        elif event == "error":
            error_message = obj.get("message") or obj.get("error") or str(obj)
            break

    return SmokeResult(
        http_status=response.status_code,
        workflow_status=workflow_status,
        workflow_run_id=workflow_run_id,
        answer="".join(answer_parts).strip(),
        error_message=error_message,
    )


def main() -> int:
    args = parse_args()
    result = run_workflow_smoke(
        base_url=args.api_base,
        app_token=args.app_token,
        query=args.query,
        user=args.user,
        timeout_sec=max(30, int(args.timeout_sec)),
    )

    payload = asdict(result)
    payload["query"] = args.query
    payload["acceptance_pass"] = (
        result.http_status == 200
        and (result.workflow_status or "").lower() in {"success", "succeeded"}
        and bool(result.answer.strip())
    )
    payload["answer_preview"] = result.answer[:300]

    if args.output_json.strip():
        out_path = Path(args.output_json).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(payload, ensure_ascii=False, indent=2))

    if payload["acceptance_pass"]:
        return 0

    print("[FAIL] dify business smoke did not pass acceptance.", file=sys.stderr)
    return 4


if __name__ == "__main__":
    raise SystemExit(main())
