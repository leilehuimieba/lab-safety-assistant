# Web Seed V5 Prefetch Report

- Total sources: `22`
- Fetchable (`status=ok`): `18` (81.8%)
- Blocked (`status=blocked`): `3` (13.6%)
- Failed (`status=error/timeout/not_found`): `1` (4.5%)
- Low quality (`quality_score < 0.70`): `2` (9.1%)

## Blocked / Failed Items (Collector First)

| source_id | status | title | suggested_action |
|---|---|---|---|
| WEB5-001 | blocked | MOE notice on Higher Education Laboratory Safety Standard | collector: replace with official mirror or provide downloadable attachment |
| WEB5-002 | blocked | MOE trial method for laboratory risk grading and classification | collector: replace with official mirror or provide downloadable attachment |
| WEB5-004 | blocked | State Council policy library relay for MOE laboratory safety standard | collector: replace with official mirror or provide downloadable attachment |
| WEB5-021 | error | Harvard EHS biological safety | collector: replace with official mirror or provide downloadable attachment |

## Low Quality Items (Cleaner First)

| source_id | status | quality_score | title | suggested_action |
|---|---|---:|---|---|
| WEB5-004 | blocked | 0.5732 | State Council policy library relay for MOE laboratory safety standard | cleaner: manually review and rewrite structured summary |
| WEB5-021 | error | 0.2532 | Harvard EHS biological safety | cleaner: manually review and rewrite structured summary |

## Import Plan

1. Import `ok` rows from `artifacts/web_seed_v5_prefetch/knowledge_base_web.csv` into staging KB.
2. Resolve blocked/error rows by collector and rerun one prefetch round.
3. Clean low-quality rows before moving to official release batch.
