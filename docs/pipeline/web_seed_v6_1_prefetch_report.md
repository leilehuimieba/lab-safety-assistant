# web_seed_v6_1 Prefetch Report

- Total sources: `12`
- Fetchable (`status=ok`): `12` (100.0%)
- Blocked (`status=blocked`): `0` (0.0%)
- Failed (`status=error/timeout/not_found`): `0` (0.0%)
- Low quality (`quality_score < 0.70`): `4` (33.3%)

## Blocked / Failed Items (Collector First)

| source_id | status | title | suggested_action |
|---|---|---|---|

## Low Quality Items (Cleaner First)

| source_id | status | quality_score | title | suggested_action |
|---|---|---:|---|---|
| WEB6-006 | ok | 0.6839 | Canadian Biosafety Standard Third Edition | cleaner: manually review and rewrite structured summary |
| WEB6-008 | ok | 0.6511 | Singapore Biosafety Information and Guidelines | cleaner: manually review and rewrite structured summary |
| WEB6-011 | ok | 0.6279 | NHC Office Notice on Strengthening Laboratory Biosafety in COVID-19 Routine Control | cleaner: manually review and rewrite structured summary |
| WEB6-012 | ok | 0.1937 | ShanghaiTech Laboratory Safety Manual PDF | cleaner: manually review and rewrite structured summary |

## Import Plan

1. Import `ok` rows from prefetch knowledge_base_web.csv into staging KB.
2. Resolve blocked/error rows by collector and rerun one prefetch round.
3. Clean low-quality rows before moving to official release batch.
