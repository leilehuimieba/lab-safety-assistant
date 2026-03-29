# web_seed_v6 Prefetch Report

- Total sources: `12`
- Fetchable (`status=ok`): `9` (75.0%)
- Blocked (`status=blocked`): `3` (25.0%)
- Failed (`status=error/timeout/not_found`): `0` (0.0%)
- Low quality (`quality_score < 0.70`): `1` (8.3%)

## Blocked / Failed Items (Collector First)

| source_id | status | title | suggested_action |
|---|---|---|---|
| WEB6-006 | blocked | Canadian Biosafety Standard Third Edition | collector: replace with official mirror or provide downloadable attachment |
| WEB6-007 | blocked | Canadian Biosafety Handbook Second Edition | collector: replace with official mirror or provide downloadable attachment |
| WEB6-009 | blocked | Singapore Biosafety Guidelines for Research 2021 | collector: replace with official mirror or provide downloadable attachment |

## Low Quality Items (Cleaner First)

| source_id | status | quality_score | title | suggested_action |
|---|---|---:|---|---|
| WEB6-011 | ok | 0.1895 | China NHC Notice on COVID-19 Laboratory Biosafety Guidance 2nd Edition | cleaner: manually review and rewrite structured summary |

## Import Plan

1. Import `ok` rows from prefetch knowledge_base_web.csv into staging KB.
2. Resolve blocked/error rows by collector and rerun one prefetch round.
3. Clean low-quality rows before moving to official release batch.
