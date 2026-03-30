# web_seed_v8_1 Prefetch Report

- Total sources: `30`
- Fetchable (`status=ok`): `18` (60.0%)
- Blocked (`status=blocked`): `12` (40.0%)
- Failed (`status=error/timeout/not_found`): `0` (0.0%)
- Low quality (`quality_score < 0.70`): `26` (86.7%)

## Blocked / Failed Items (Collector First)

| source_id | status | title | suggested_action |
|---|---|---|---|
| WEB8-001 | blocked | OSHA Laboratory Standards | collector: replace with official mirror or provide downloadable attachment |
| WEB8-002 | blocked | OSHA Culture of Safety for Laboratories | collector: replace with official mirror or provide downloadable attachment |
| WEB8-003 | blocked | OSHA Hazard Recognition and Solutions for Laboratories | collector: replace with official mirror or provide downloadable attachment |
| WEB8-004 | blocked | OSHA Laboratory Additional Resources | collector: replace with official mirror or provide downloadable attachment |
| WEB8-005 | blocked | OSHA Laboratory Safety Guidance PDF | collector: replace with official mirror or provide downloadable attachment |
| WEB8-006 | blocked | OSHA Lab Standard Fact Sheet PDF | collector: replace with official mirror or provide downloadable attachment |
| WEB8-007 | blocked | OSHA Chemical Hygiene Plan Fact Sheet PDF | collector: replace with official mirror or provide downloadable attachment |
| WEB8-008 | blocked | OSHA Chemical Fume Hoods QuickFacts PDF | collector: replace with official mirror or provide downloadable attachment |
| WEB8-009 | blocked | OSHA Biosafety Cabinets Fact Sheet PDF | collector: replace with official mirror or provide downloadable attachment |
| WEB8-010 | blocked | OSHA Electrical Hazards in Labs QuickFacts PDF | collector: replace with official mirror or provide downloadable attachment |
| WEB8-029 | blocked | UCSF Chemical Safety | collector: replace with official mirror or provide downloadable attachment |
| WEB8-030 | blocked | UCSF Fire and Life Safety | collector: replace with official mirror or provide downloadable attachment |

## Low Quality Items (Cleaner First)

| source_id | status | quality_score | title | suggested_action |
|---|---|---:|---|---|
| WEB8-001 | blocked | 0.2315 | OSHA Laboratory Standards | cleaner: manually review and rewrite structured summary |
| WEB8-002 | blocked | 0.2307 | OSHA Culture of Safety for Laboratories | cleaner: manually review and rewrite structured summary |
| WEB8-003 | blocked | 0.2330 | OSHA Hazard Recognition and Solutions for Laboratories | cleaner: manually review and rewrite structured summary |
| WEB8-004 | blocked | 0.2330 | OSHA Laboratory Additional Resources | cleaner: manually review and rewrite structured summary |
| WEB8-005 | blocked | 0.2300 | OSHA Laboratory Safety Guidance PDF | cleaner: manually review and rewrite structured summary |
| WEB8-006 | blocked | 0.2304 | OSHA Lab Standard Fact Sheet PDF | cleaner: manually review and rewrite structured summary |
| WEB8-007 | blocked | 0.2311 | OSHA Chemical Hygiene Plan Fact Sheet PDF | cleaner: manually review and rewrite structured summary |
| WEB8-008 | blocked | 0.2288 | OSHA Chemical Fume Hoods QuickFacts PDF | cleaner: manually review and rewrite structured summary |
| WEB8-009 | blocked | 0.2315 | OSHA Biosafety Cabinets Fact Sheet PDF | cleaner: manually review and rewrite structured summary |
| WEB8-010 | blocked | 0.2307 | OSHA Electrical Hazards in Labs QuickFacts PDF | cleaner: manually review and rewrite structured summary |
| WEB8-011 | ok | 0.4559 | CDC Laboratories About | cleaner: manually review and rewrite structured summary |
| WEB8-012 | ok | 0.2903 | CDC Laboratory Services | cleaner: manually review and rewrite structured summary |
| WEB8-014 | ok | 0.5416 | CDC Laboratory Partners and Readiness | cleaner: manually review and rewrite structured summary |
| WEB8-016 | ok | 0.5059 | CDC CLIA Certificates | cleaner: manually review and rewrite structured summary |
| WEB8-017 | ok | 0.6612 | CDC BMBL 6th Edition | cleaner: manually review and rewrite structured summary |
| WEB8-018 | ok | 0.4521 | CDC Animal Care Regulations and Standards | cleaner: manually review and rewrite structured summary |
| WEB8-020 | ok | 0.6842 | Purdue Chemical Hygiene Plan | cleaner: manually review and rewrite structured summary |
| WEB8-021 | ok | 0.6786 | Purdue Hazard Communication | cleaner: manually review and rewrite structured summary |
| WEB8-022 | ok | 0.6827 | Purdue Laboratory SOPs | cleaner: manually review and rewrite structured summary |
| WEB8-023 | ok | 0.6832 | Purdue Biological Materials Safety | cleaner: manually review and rewrite structured summary |
| WEB8-024 | ok | 0.6854 | Purdue Chemical Materials Management | cleaner: manually review and rewrite structured summary |
| WEB8-025 | ok | 0.6695 | Purdue Laboratory Spill Response | cleaner: manually review and rewrite structured summary |
| WEB8-026 | ok | 0.1979 | BU Laboratory Safety Program | cleaner: manually review and rewrite structured summary |
| WEB8-028 | ok | 0.3712 | BU Biosafety Manual | cleaner: manually review and rewrite structured summary |
| WEB8-029 | blocked | 0.0000 | UCSF Chemical Safety | cleaner: manually review and rewrite structured summary |
| WEB8-030 | blocked | 0.0000 | UCSF Fire and Life Safety | cleaner: manually review and rewrite structured summary |

## Import Plan

1. Import `ok` rows from prefetch knowledge_base_web.csv into staging KB.
2. Resolve blocked/error rows by collector and rerun one prefetch round.
3. Clean low-quality rows before moving to official release batch.
