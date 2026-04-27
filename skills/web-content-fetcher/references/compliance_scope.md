# Compliance Scope

This skill is intended for lawful, research-oriented extraction of public web content.

## Allowed Use

- Public pages accessible without bypassing authentication
- Research and experiment data collection
- Internal QA, retrieval benchmarking, and knowledge base construction

## Not Allowed

- Bypassing logins, paywalls, or access controls
- Ignoring website terms of service
- Bulk crawling that harms service availability

## Required Output Behavior

- If content is blocked or requires auth, set:
  - `status=blocked`
  - `requires_auth=true`
  - `error_reason` with explicit cause
- Do not fabricate summaries from incomplete extraction.

## Data Hygiene

- Keep `url`, `provider`, and `fetched_at` for traceability.
- Store only required text slices for experiments.
- Prefer references and citations over full content redistribution.

