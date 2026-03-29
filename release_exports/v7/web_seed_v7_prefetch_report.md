# web_seed_v7 Prefetch Report

- Total sources: `14`
- Fetchable (`status=ok`): `14` (100.0%)
- Blocked (`status=blocked`): `0` (0.0%)
- Failed (`status=error/timeout/not_found`): `0` (0.0%)
- Low quality (`quality_score < 0.70`): `3` (21.4%)

## Blocked / Failed Items (Collector First)

| source_id | status | title | suggested_action |
|---|---|---|---|

## Low Quality Items (Cleaner First)

| source_id | status | quality_score | title | suggested_action |
|---|---|---:|---|---|
| WEB7-001 | ok | 0.6682 | CDC COVID-19 Laboratory Safety Resources | cleaner: manually review and rewrite structured summary |
| WEB7-002 | ok | 0.6843 | OSHA Fact Sheet Laboratory Safety and the OSHA Laboratory Standard | cleaner: manually review and rewrite structured summary |
| WEB7-006 | ok | 0.6970 | CDC Strong Laboratory Safety Program | cleaner: manually review and rewrite structured summary |

## Import Plan

1. Import `ok` rows from prefetch knowledge_base_web.csv into staging KB.
2. Resolve blocked/error rows by collector and rerun one prefetch round.
3. Clean low-quality rows before moving to official release batch.
