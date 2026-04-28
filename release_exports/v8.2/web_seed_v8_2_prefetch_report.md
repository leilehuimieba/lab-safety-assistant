# web_seed_v8_2 Prefetch Report

- Total sources: `30`
- Fetchable (`status=ok`): `30` (100.0%)
- Blocked (`status=blocked`): `0` (0.0%)
- Failed (`status=error/timeout/not_found`): `0` (0.0%)
- Low quality (`quality_score < 0.70`): `3` (10.0%)

## Blocked / Failed Items (Collector First)

| source_id | status | title | suggested_action |
|---|---|---|---|

## Low Quality Items (Cleaner First)

| source_id | status | quality_score | title | suggested_action |
|---|---|---:|---|---|
| WEB82-024 | ok | 0.6597 | HSE Biosafety Blood-borne Viruses | cleaner: manually review and rewrite structured summary |
| WEB82-026 | ok | 0.6739 | HSE Biosafety Infection | cleaner: manually review and rewrite structured summary |
| WEB82-027 | ok | 0.6558 | HSE COSHH | cleaner: manually review and rewrite structured summary |

## Import Plan

1. Import `ok` rows from prefetch knowledge_base_web.csv into staging KB.
2. Resolve blocked/error rows by collector and rerun one prefetch round.
3. Clean low-quality rows before moving to official release batch.
