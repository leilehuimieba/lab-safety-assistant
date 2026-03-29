# web_seed_v8 Prefetch Report

- Total sources: `30`
- Fetchable (`status=ok`): `30` (100.0%)
- Blocked (`status=blocked`): `0` (0.0%)
- Failed (`status=error/timeout/not_found`): `0` (0.0%)
- Low quality (`quality_score < 0.70`): `30` (100.0%)

## Blocked / Failed Items (Collector First)

| source_id | status | title | suggested_action |
|---|---|---|---|

## Low Quality Items (Cleaner First)

| source_id | status | quality_score | title | suggested_action |
|---|---|---:|---|---|
| WEB8-001 | ok | 0.0000 | OSHA Laboratory Standards | cleaner: manually review and rewrite structured summary |
| WEB8-002 | ok | 0.0000 | OSHA Culture of Safety for Laboratories | cleaner: manually review and rewrite structured summary |
| WEB8-003 | ok | 0.0000 | OSHA Hazard Recognition and Solutions for Laboratories | cleaner: manually review and rewrite structured summary |
| WEB8-004 | ok | 0.0000 | OSHA Laboratory Additional Resources | cleaner: manually review and rewrite structured summary |
| WEB8-005 | ok | 0.0000 | OSHA Laboratory Safety Guidance PDF | cleaner: manually review and rewrite structured summary |
| WEB8-006 | ok | 0.0000 | OSHA Lab Standard Fact Sheet PDF | cleaner: manually review and rewrite structured summary |
| WEB8-007 | ok | 0.0000 | OSHA Chemical Hygiene Plan Fact Sheet PDF | cleaner: manually review and rewrite structured summary |
| WEB8-008 | ok | 0.0000 | OSHA Chemical Fume Hoods QuickFacts PDF | cleaner: manually review and rewrite structured summary |
| WEB8-009 | ok | 0.0000 | OSHA Biosafety Cabinets Fact Sheet PDF | cleaner: manually review and rewrite structured summary |
| WEB8-010 | ok | 0.0000 | OSHA Electrical Hazards in Labs QuickFacts PDF | cleaner: manually review and rewrite structured summary |
| WEB8-011 | ok | 0.0000 | CDC Laboratories About | cleaner: manually review and rewrite structured summary |
| WEB8-012 | ok | 0.0000 | CDC Laboratory Services | cleaner: manually review and rewrite structured summary |
| WEB8-013 | ok | 0.0000 | CDC Laboratories Programs | cleaner: manually review and rewrite structured summary |
| WEB8-014 | ok | 0.0000 | CDC Laboratory Partners and Readiness | cleaner: manually review and rewrite structured summary |
| WEB8-015 | ok | 0.0000 | CDC Laboratory Quality | cleaner: manually review and rewrite structured summary |
| WEB8-016 | ok | 0.0000 | CDC CLIA Certificates | cleaner: manually review and rewrite structured summary |
| WEB8-017 | ok | 0.0000 | CDC BMBL 6th Edition | cleaner: manually review and rewrite structured summary |
| WEB8-018 | ok | 0.0000 | CDC Animal Care Regulations and Standards | cleaner: manually review and rewrite structured summary |
| WEB8-019 | ok | 0.0000 | Purdue Laboratory Researchers Guide | cleaner: manually review and rewrite structured summary |
| WEB8-020 | ok | 0.0000 | Purdue Chemical Hygiene Plan | cleaner: manually review and rewrite structured summary |
| WEB8-021 | ok | 0.0000 | Purdue Hazard Communication | cleaner: manually review and rewrite structured summary |
| WEB8-022 | ok | 0.0000 | Purdue Laboratory SOPs | cleaner: manually review and rewrite structured summary |
| WEB8-023 | ok | 0.0000 | Purdue Biological Materials Safety | cleaner: manually review and rewrite structured summary |
| WEB8-024 | ok | 0.0000 | Purdue Chemical Materials Management | cleaner: manually review and rewrite structured summary |
| WEB8-025 | ok | 0.0000 | Purdue Laboratory Spill Response | cleaner: manually review and rewrite structured summary |
| WEB8-026 | ok | 0.0000 | BU Laboratory Safety Program | cleaner: manually review and rewrite structured summary |
| WEB8-027 | ok | 0.0000 | BU Chemical Hygiene Plan | cleaner: manually review and rewrite structured summary |
| WEB8-028 | ok | 0.0000 | BU Biosafety Manual | cleaner: manually review and rewrite structured summary |
| WEB8-029 | ok | 0.0000 | UCSF Chemical Safety | cleaner: manually review and rewrite structured summary |
| WEB8-030 | ok | 0.0000 | UCSF Fire and Life Safety | cleaner: manually review and rewrite structured summary |

## Import Plan

1. Import `ok` rows from prefetch knowledge_base_web.csv into staging KB.
2. Resolve blocked/error rows by collector and rerun one prefetch round.
3. Clean low-quality rows before moving to official release batch.
