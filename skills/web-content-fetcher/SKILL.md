---
name: web-content-fetcher
description: Multi-channel webpage body extraction for URL reading and summarization tasks. Use when a user asks to read links, extract article正文, summarize webpage content, or ingest web pages into a knowledge base. This skill routes requests across Jina, Scrapling, and direct HTML fallback, then returns structured output with provider, quality score, and explicit failure reason to avoid hallucinated summaries.
---

# Web Content Fetcher

## Overview

Use this skill to extract webpage正文 before summarization or KB ingestion.
Always extract first, summarize second. If extraction fails, report failure clearly instead of guessing.

## Workflow

1. Run `scripts/fetch_web_content.py` with one or more URLs.
2. Check `status`, `provider`, `quality_score`, and `requires_auth`.
3. If `status=ok`, use `content` for summarization/ingestion.
4. If `status=blocked` or `status=error`, return the reason and next action.
5. For ingestion, save JSON output and hand it to downstream cleaning/chunking steps.

## Quick Commands

Single URL:

```powershell
python skills/web-content-fetcher/scripts/fetch_web_content.py `
  --url "https://example.com/post" `
  --max-chars 30000
```

Batch URLs:

```powershell
python skills/web-content-fetcher/scripts/fetch_web_content.py `
  --url-file data_sources/web_seed_urls.csv `
  --url-column url `
  --out-json artifacts/web_fetch_output.json `
  --max-chars 30000
```

Force provider order:

```powershell
python skills/web-content-fetcher/scripts/fetch_web_content.py `
  --url "https://example.com/post" `
  --providers "jina,scrapling,direct"
```

## Output Contract

Each record contains:

- `url`: requested URL
- `status`: `ok | blocked | error`
- `provider`: `jina | scrapling | direct`
- `title`: extracted title (best effort)
- `content`: cleaned正文 (clipped by `max_chars`)
- `quality_score`: 0.0 to 1.0 heuristic
- `requires_auth`: whether login wall is likely
- `error_reason`: explicit reason when failed or blocked
- `fetched_at`: UTC timestamp

## Routing Notes

- Default order is `jina -> scrapling -> direct`.
- For domains commonly blocked in reader mode (for example `weixin.qq.com`, `xiaohongshu.com`), the script moves `scrapling` to the front when available.
- `max_chars` defaults to `30000` to balance token cost and content completeness.

## Compliance Guardrails

- Extract only pages that are publicly reachable in your current environment.
- Do not bypass authentication, paid walls, or access controls.
- If a page requires login, return `requires_auth=true` and stop fabricating content.
- Keep source URL and provider in output for traceability.

Read `references/compliance_scope.md` before production ingestion.

## Resources

- `scripts/fetch_web_content.py`: extraction router and CLI
- `references/provider_routing.md`: routing and fallback policy
- `references/compliance_scope.md`: legal and data handling boundaries
