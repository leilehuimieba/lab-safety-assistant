# Live Regression Guardrail Round (2026-03-29)

## Scope
- Objective: execute the high-value loop (`Top10-driven patch -> live recheck -> compare`).
- Workflow:
  - `workflow_id`: `d3e2be2d-c487-4dea-b9ed-8e374ba7ea07`
  - `app_id`: `cc562e30-53af-41fd-bb66-0145e7b0ff81`
- Eval command baseline:
  - `python scripts/run_eval_regression_pipeline.py --repo-root . --dify-base-url http://localhost:8080 --dify-app-key <token> --dify-response-mode streaming --limit 20 --dify-timeout 60 --eval-concurrency 1 --update-dashboard`

## Changes Applied
1. Added structured prompt patch tool:
   - `scripts/patch_workflow_prompt_guardrails.py`
   - Applies strict output schema (`answer/steps/ppe/forbidden/emergency`) and safety behavior rules.
   - Backup:
     - `artifacts/workflow_patches/run_20260329_093041/workflow_d3e2be2d-c487-4dea-b9ed-8e374ba7ea07_backup_before_guardrails.json`
2. Fixed refusal detection quality:
   - `scripts/eval_smoke.py`
   - Replaced mojibake refusal hints, added robust prefix pattern for Chinese refusal phrasing.
3. Added/updated tests:
   - `tests/test_patch_workflow_prompt_guardrails.py`
   - `tests/test_eval_smoke.py`
4. Temporary reliability patch for retrieval outage:
   - Disabled retrieval node to bypass embedding channel failure (`host.docker.internal:11434` unreachable).
   - Backup:
     - `artifacts/workflow_patches/run_20260329_094512/workflow_d3e2be2d-c487-4dea-b9ed-8e374ba7ea07_backup.json`

## Run Comparison

| run_id | setup | safety_refusal_rate | emergency_pass_rate | qa_pass_rate | coverage_rate | latency_p95_ms |
|---|---|---:|---:|---:|---:|---:|
| `run_20260329_091646` | baseline (before this round) | 0.25 | 0.20 | 0.1818 | 0.80 | 60218.73 |
| `run_20260329_093311` | guardrail prompt, retrieval on | 0.75 | 0.40 | 0.0909 | 1.00 | 13534.53 |
| `run_20260329_093750` | guardrail prompt, retrieval on (service unstable) | 0.00 | 0.00 | 0.0909 | 0.05 | 61525.40 |
| `run_20260329_094525` | guardrail prompt, retrieval off | 0.50 | 0.60 | 0.4545 | 0.95 | 19266.44 |
| `run_20260329_095243` | retrieval off + refusal detection fix | **1.00** | 0.40 | 0.3636 | **1.00** | 16915.20 |

## Key Findings
- Positive:
  - `safety_refusal_rate` reached target in latest run (`1.00 >= 0.95`).
  - Coverage recovered to `1.00` after bypassing retrieval failure point.
  - Top failure class shifted from infra (`fetch_error`) to content quality (`missing_keypoints`), which is actionable.
- Remaining gap:
  - `emergency_pass_rate` and `qa_pass_rate` remain below target.
  - Latest dominant failure reason is `missing_keypoints` (80% of failed rows).
- Infra risk (root cause already confirmed in worker logs):
  - Embedding channel intermittently unavailable:
    - `host.docker.internal:11434` unreachable
    - upstream SSL/API instability on model provider path

## Next High-Value Actions
1. Content-first fix:
   - Add emergency/QA-specific structured micro-templates to LLM prompt (for Top10 IDs).
   - Goal: reduce `missing_keypoints` by forcing higher keypoint density in `steps` and `emergency`.
2. Reliability fix:
   - Keep a retrieval-off fallback path for regression stability.
   - In parallel, repair embedding endpoint connectivity and then re-enable retrieval for final release mode.
3. Release policy:
   - Use this round as a safety-metric recovery checkpoint.
   - Do not mark release-ready until `qa_pass_rate >= 0.85` and `emergency_pass_rate >= 0.9` under stable infra.
