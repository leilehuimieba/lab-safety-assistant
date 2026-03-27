#!/usr/bin/env python3
"""
AI-only review and recheck for KB CSV rows.

Goals:
- Stage 1 (audit): initial AI review for all candidate rows.
- Stage 2 (recheck): stricter AI recheck for rows that passed stage 1.
- Export pass/block CSVs and machine-readable report for gates/pipelines.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


KB_FIELDNAMES = [
    "id",
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
    "last_updated",
    "reviewer",
    "status",
    "tags",
    "language",
]

AI_FIELDNAMES = [
    "ai_stage",
    "ai_model",
    "ai_decision",
    "ai_score",
    "ai_safety_ok",
    "ai_grounding_ok",
    "ai_actionability_ok",
    "ai_confidence",
    "ai_issues",
    "ai_rewrite_suggestion",
    "ai_post_rule",
    "ai_pass",
    "ai_error",
    "ai_reviewed_at",
]

DEFAULT_BASE_URL = "http://ai.little100.cn:3000/v1"
DEFAULT_MODEL = "gpt-5.2-codex"
DEFAULT_FALLBACK_MODELS = "grok-3-mini,grok-4,grok-3"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI review/recheck for KB CSV.")
    parser.add_argument("--input-csv", required=True, help="Input KB CSV path.")
    parser.add_argument(
        "--output-dir",
        default="artifacts/ai_review",
        help="Output directory for reviewed/pass/block files.",
    )
    parser.add_argument(
        "--stage",
        choices=["audit", "recheck"],
        default="audit",
        help="Review stage mode.",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=75,
        help="Minimum score required for ai_pass=yes.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional row limit for quick runs (0 = all).",
    )
    parser.add_argument(
        "--openai-base-url",
        default=os.environ.get("OPENAI_BASE_URL", DEFAULT_BASE_URL),
        help="OpenAI-compatible base URL.",
    )
    parser.add_argument(
        "--openai-api-key",
        default=os.environ.get("OPENAI_API_KEY", ""),
        help="OpenAI-compatible API key.",
    )
    parser.add_argument(
        "--openai-model",
        default=os.environ.get("OPENAI_MODEL", DEFAULT_MODEL),
        help="Primary review model.",
    )
    parser.add_argument(
        "--openai-api",
        default=os.environ.get("OPENAI_API", "auto"),
        help="API mode: auto | chat-completions | responses | openai-responses",
    )
    parser.add_argument(
        "--openai-fallback-models",
        default=os.environ.get("OPENAI_FALLBACK_MODELS", DEFAULT_FALLBACK_MODELS),
        help="Comma-separated fallback models.",
    )
    parser.add_argument(
        "--openai-timeout",
        type=float,
        default=float(os.environ.get("OPENAI_TIMEOUT", "60")),
        help="HTTP timeout seconds for model calls.",
    )
    parser.add_argument(
        "--openai-insecure-tls",
        action="store_true",
        default=(os.environ.get("OPENAI_INSECURE_TLS", "").strip().lower() in {"1", "true", "yes"}),
        help="Disable TLS certificate verification for model endpoint (temporary fallback only).",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.1,
        help="Model temperature for review calls.",
    )
    parser.add_argument(
        "--strict-high-risk",
        action="store_true",
        help="Require high-risk rows to include forbidden/emergency hints.",
    )
    return parser.parse_args()


def resolve_endpoint(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/v1"):
        return f"{normalized}/chat/completions"
    return f"{normalized}/v1/chat/completions"


def resolve_responses_endpoints(base_url: str) -> list[str]:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/chat/completions"):
        normalized = normalized[: -len("/chat/completions")]

    candidates = [f"{normalized}/responses"]
    if normalized.endswith("/v1"):
        candidates.append(f"{normalized[:-3]}/responses")
    else:
        candidates.append(f"{normalized}/v1/responses")

    dedup: list[str] = []
    for item in candidates:
        if item and item not in dedup:
            dedup.append(item)
    return dedup


def split_csv_tokens(raw: str) -> list[str]:
    return [item.strip() for item in (raw or "").split(",") if item.strip()]


def read_csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = list(reader)
    return headers, rows


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def clip(value: str, max_chars: int) -> str:
    value = (value or "").strip()
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 3] + "..."


def row_payload_for_review(row: dict[str, str]) -> dict[str, str]:
    return {
        "id": row.get("id", ""),
        "title": clip(row.get("title", ""), 220),
        "category": row.get("category", ""),
        "subcategory": row.get("subcategory", ""),
        "lab_type": row.get("lab_type", ""),
        "risk_level": row.get("risk_level", ""),
        "question": clip(row.get("question", ""), 600),
        "answer": clip(row.get("answer", ""), 1600),
        "steps": clip(row.get("steps", ""), 700),
        "ppe": clip(row.get("ppe", ""), 300),
        "forbidden": clip(row.get("forbidden", ""), 300),
        "emergency": clip(row.get("emergency", ""), 400),
        "references": clip(row.get("references", ""), 400),
        "source_url": clip(row.get("source_url", ""), 240),
        "status": row.get("status", ""),
        "tags": clip(row.get("tags", ""), 240),
        "language": row.get("language", ""),
    }


def build_prompts(stage: str, row: dict[str, str]) -> tuple[str, str]:
    strict_hint = (
        "You are doing strict second-pass quality control. Only PASS when the entry is clearly safe,"
        " grounded, and action-oriented."
        if stage == "recheck"
        else "You are doing first-pass quality control."
    )
    system_prompt = (
        "You are a lab-safety KB quality auditor.\n"
        f"{strict_hint}\n"
        "Review one knowledge-base entry and return ONLY JSON with keys:\n"
        "decision, score, safety_ok, grounding_ok, actionability_ok, confidence, issues, rewrite_suggestion.\n"
        "Rules:\n"
        "- decision: pass | needs_fix | reject\n"
        "- score: integer 0-100\n"
        "- safety_ok/grounding_ok/actionability_ok: boolean\n"
        "- confidence: high | medium | low\n"
        "- issues: short list (max 5)\n"
        "- rewrite_suggestion: short text (empty if pass)\n"
        "Focus on: dangerous guidance risk, factual grounding, actionable clarity."
    )
    user_prompt = (
        "Evaluate this KB row:\n"
        + json.dumps(row_payload_for_review(row), ensure_ascii=False, indent=2)
    )
    return system_prompt, user_prompt


def extract_text_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        return "\n".join(parts).strip()
    return ""


def extract_first_json_object(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    if text.startswith("{") and text.endswith("}"):
        return text

    start_positions = [idx for idx, ch in enumerate(text) if ch == "{"]
    for start in start_positions:
        depth = 0
        in_string = False
        escape = False
        for idx in range(start, len(text)):
            ch = text[idx]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start : idx + 1]
    return ""


def parse_review_json(raw_text: str) -> tuple[dict[str, Any], str]:
    candidate = extract_first_json_object(raw_text)
    if not candidate:
        return {}, "missing_json_object"
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        return {}, f"invalid_json:{exc}"
    if not isinstance(parsed, dict):
        return {}, "json_not_object"
    return parsed, ""


def normalize_decision(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if raw in {"pass", "needs_fix", "reject"}:
        return raw
    return "needs_fix"


def normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    raw = str(value or "").strip().lower()
    return raw in {"true", "yes", "1", "y"}


def normalize_confidence(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if raw in {"high", "medium", "low"}:
        return raw
    return "medium"


def normalize_issues(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()][:5]
    if isinstance(value, str) and value.strip():
        parts = re.split(r"[;；\n]+", value.strip())
        return [item.strip() for item in parts if item.strip()][:5]
    return []


def normalize_score(value: Any) -> int:
    try:
        score = int(float(value))
    except Exception:
        return 0
    return max(0, min(100, score))


def call_model(
    *,
    endpoint: str,
    api_key: str,
    models: list[str],
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    timeout: float,
    insecure_tls: bool,
    api_mode: str,
) -> tuple[str, str, str]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    last_error = "unknown_error"
    ssl_context = ssl._create_unverified_context() if insecure_tls else None

    mode = (api_mode or "auto").strip().lower()
    if mode in {"openai-responses", "responses"}:
        mode_list = ["responses"]
    elif mode in {"chat", "chat-completions", "chat_completions"}:
        mode_list = ["chat"]
    else:
        mode_list = ["chat", "responses"]

    def call_chat(model: str) -> tuple[str, str]:
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            endpoint,
            data=data,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout, context=ssl_context) as response:
            raw = response.read().decode("utf-8", errors="ignore")
        payload = json.loads(raw)
        return extract_text_content(payload), ""

    def call_responses(model: str) -> tuple[str, str]:
        body = {
            "model": model,
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": True,
        }
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        last_mode_error = ""
        for responses_endpoint in resolve_responses_endpoints(endpoint):
            request = urllib.request.Request(
                responses_endpoint,
                data=data,
                headers=headers,
                method="POST",
            )
            try:
                text_parts: list[str] = []
                with urllib.request.urlopen(request, timeout=timeout, context=ssl_context) as response:
                    for raw_line in response:
                        line = raw_line.decode("utf-8", errors="ignore").strip()
                        if not line.startswith("data:"):
                            continue
                        payload = line[5:].strip()
                        if not payload:
                            continue
                        try:
                            event = json.loads(payload)
                        except json.JSONDecodeError:
                            continue
                        etype = str(event.get("type") or "")
                        if etype == "response.output_text.delta":
                            delta = event.get("delta")
                            if isinstance(delta, str) and delta:
                                text_parts.append(delta)
                        elif etype == "response.output_text.done":
                            text_done = event.get("text")
                            if isinstance(text_done, str) and text_done and not text_parts:
                                text_parts.append(text_done)
                        elif etype == "response.completed":
                            break
                text = "".join(text_parts).strip()
                if text:
                    return text, ""
                last_mode_error = f"empty_response_text:{responses_endpoint}"
            except urllib.error.HTTPError as exc:
                msg = exc.read().decode("utf-8", errors="ignore")[:500]
                last_mode_error = f"http_{exc.code}:{msg}"
                if exc.code in {404, 405}:
                    continue
                return "", last_mode_error
            except Exception as exc:  # noqa: BLE001
                last_mode_error = f"request_error:{exc}"
                continue
        return "", last_mode_error or "responses_request_failed"

    for model in models:
        for mode_item in mode_list:
            try:
                if mode_item == "chat":
                    text, _ = call_chat(model)
                else:
                    text, mode_error = call_responses(model)
                    if mode_error:
                        last_error = mode_error
                        continue
            except urllib.error.HTTPError as exc:
                msg = exc.read().decode("utf-8", errors="ignore")[:500]
                last_error = f"http_{exc.code}:{msg}"
                if "model_not_found" in msg or "No available OpenAI account supports the requested model" in msg:
                    break
                continue
            except Exception as exc:  # noqa: BLE001
                last_error = f"request_error:{exc}"
                continue

            if text:
                return text, model, ""
            last_error = f"empty_response_text:{mode_item}"
    return "", "", last_error


def post_rule_check(row: dict[str, str], strict_high_risk: bool) -> str:
    issues: list[str] = []
    answer = (row.get("answer") or "").strip()
    if len(answer) < 60:
        issues.append("answer_too_short")

    if strict_high_risk:
        try:
            risk_level = int((row.get("risk_level") or "0").strip() or "0")
        except ValueError:
            risk_level = 0
        if risk_level >= 4:
            if not (row.get("forbidden") or "").strip():
                issues.append("high_risk_missing_forbidden")
            if not (row.get("emergency") or "").strip():
                issues.append("high_risk_missing_emergency")
    return ";".join(issues)


def normalize_kb_row(row: dict[str, str]) -> dict[str, str]:
    return {field: (row.get(field) or "").strip() for field in KB_FIELDNAMES}


def build_pass_row(
    row: dict[str, str],
    *,
    stage: str,
    ai_model: str,
    ai_score: int,
    ai_decision: str,
) -> dict[str, str]:
    normalized = normalize_kb_row(row)
    normalized["status"] = f"ai_passed_{stage}"
    normalized["reviewer"] = f"ai-review:{ai_model}"
    normalized["last_updated"] = today_str()
    legal = normalized.get("legal_notes", "")
    tag = f"[AI review stage={stage} decision={ai_decision} score={ai_score}]"
    normalized["legal_notes"] = f"{legal} {tag}".strip()
    return normalized


def main() -> int:
    args = parse_args()

    input_csv = Path(args.input_csv).resolve()
    if not input_csv.exists():
        raise SystemExit(f"Input CSV not found: {input_csv}")

    if not args.openai_api_key.strip():
        raise SystemExit("Missing API key. Set OPENAI_API_KEY or use --openai-api-key.")

    headers, rows = read_csv_rows(input_csv)
    if not headers:
        raise SystemExit(f"Input CSV has empty headers: {input_csv}")
    if args.limit > 0:
        rows = rows[: args.limit]

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    reviewed_csv = output_dir / f"ai_review_{args.stage}.csv"
    pass_csv = output_dir / f"knowledge_base_{args.stage}_pass.csv"
    blocked_csv = output_dir / f"knowledge_base_{args.stage}_blocked.csv"
    report_json = output_dir / f"ai_review_report_{args.stage}.json"

    endpoint = resolve_endpoint(args.openai_base_url)
    models = [args.openai_model.strip(), *split_csv_tokens(args.openai_fallback_models)]
    unique_models: list[str] = []
    for model in models:
        if model and model not in unique_models:
            unique_models.append(model)

    reviewed_rows: list[dict[str, Any]] = []
    pass_rows: list[dict[str, str]] = []
    blocked_rows: list[dict[str, Any]] = []

    decision_stat = {"pass": 0, "needs_fix": 0, "reject": 0}
    parse_errors = 0
    call_errors = 0
    post_rule_hits = 0

    for index, row in enumerate(rows, start=1):
        system_prompt, user_prompt = build_prompts(args.stage, row)
        raw_text, used_model, call_error = call_model(
            endpoint=endpoint,
            api_key=args.openai_api_key.strip(),
            models=unique_models,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=args.temperature,
            timeout=args.openai_timeout,
            insecure_tls=args.openai_insecure_tls,
            api_mode=args.openai_api,
        )

        parsed: dict[str, Any] = {}
        parse_error = ""
        if not call_error:
            parsed, parse_error = parse_review_json(raw_text)
        if call_error:
            call_errors += 1
        if parse_error:
            parse_errors += 1

        decision = normalize_decision(parsed.get("decision"))
        score = normalize_score(parsed.get("score"))
        safety_ok = normalize_bool(parsed.get("safety_ok"))
        grounding_ok = normalize_bool(parsed.get("grounding_ok"))
        actionability_ok = normalize_bool(parsed.get("actionability_ok"))
        confidence = normalize_confidence(parsed.get("confidence"))
        issues = normalize_issues(parsed.get("issues"))
        rewrite_suggestion = str(parsed.get("rewrite_suggestion") or "").strip()

        post_rule = post_rule_check(row, strict_high_risk=args.strict_high_risk)
        if post_rule:
            post_rule_hits += 1

        ai_pass = (
            decision == "pass"
            and score >= args.min_score
            and safety_ok
            and grounding_ok
            and actionability_ok
            and not post_rule
            and not call_error
            and not parse_error
        )

        if decision not in decision_stat:
            decision = "needs_fix"
        decision_stat[decision] += 1

        reviewed_at = now_iso()
        issue_text = ";".join(issues)
        error_text = ";".join(item for item in [call_error, parse_error] if item)
        ai_fields = {
            "ai_stage": args.stage,
            "ai_model": used_model or args.openai_model,
            "ai_decision": decision,
            "ai_score": score,
            "ai_safety_ok": "yes" if safety_ok else "no",
            "ai_grounding_ok": "yes" if grounding_ok else "no",
            "ai_actionability_ok": "yes" if actionability_ok else "no",
            "ai_confidence": confidence,
            "ai_issues": issue_text,
            "ai_rewrite_suggestion": rewrite_suggestion,
            "ai_post_rule": post_rule,
            "ai_pass": "yes" if ai_pass else "no",
            "ai_error": error_text,
            "ai_reviewed_at": reviewed_at,
        }

        reviewed_row = {**row, **ai_fields}
        reviewed_rows.append(reviewed_row)

        if ai_pass:
            pass_rows.append(
                build_pass_row(
                    row,
                    stage=args.stage,
                    ai_model=ai_fields["ai_model"],
                    ai_score=score,
                    ai_decision=decision,
                )
            )
        else:
            blocked_rows.append(reviewed_row)

        print(
            f"[{index}/{len(rows)}] id={row.get('id','')} decision={decision} "
            f"score={score} pass={'yes' if ai_pass else 'no'}"
        )

    write_csv(reviewed_csv, headers + AI_FIELDNAMES, reviewed_rows)
    write_csv(pass_csv, KB_FIELDNAMES, pass_rows)
    write_csv(blocked_csv, headers + AI_FIELDNAMES, blocked_rows)

    total = len(rows)
    pass_count = len(pass_rows)
    report = {
        "generated_at": now_iso(),
        "stage": args.stage,
        "input_csv": str(input_csv),
        "reviewed_csv": str(reviewed_csv),
        "pass_csv": str(pass_csv),
        "blocked_csv": str(blocked_csv),
        "total_rows": total,
        "pass_rows": pass_count,
        "blocked_rows": len(blocked_rows),
        "pass_rate": round((pass_count / total), 4) if total else 0.0,
        "call_error_count": call_errors,
        "call_error_rate": round((call_errors / total), 4) if total else 0.0,
        "parse_error_count": parse_errors,
        "parse_error_rate": round((parse_errors / total), 4) if total else 0.0,
        "post_rule_hits": post_rule_hits,
        "decision_stat": decision_stat,
        "min_score": args.min_score,
        "strict_high_risk": bool(args.strict_high_risk),
        "openai_insecure_tls": bool(args.openai_insecure_tls),
        "openai_api": args.openai_api,
        "models": unique_models,
    }
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"AI review stage done: {args.stage}")
    print(f"- reviewed: {reviewed_csv}")
    print(f"- pass:     {pass_csv}")
    print(f"- blocked:  {blocked_csv}")
    print(f"- report:   {report_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
