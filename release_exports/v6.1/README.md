# Release Export v6.1

- generated_at: 2026-03-29 18:21:34
- import_ready_rows: 336
- source_priority: curated > v6_1_web_rewritten > v5_web > v4_2_release

## Notes
- V6.1 improves fetch availability to 12/12 by fixing auth-wall false positives in web-content-fetcher.
- Low-quality rows are auto-rewritten into structured fields (answer/steps/ppe/forbidden/emergency).
- AI audit call reached model gateway but returned server-side account misconfiguration for this endpoint.

## Included files
1. knowledge_base_import_ready.csv
2. import_bundle_report.json / import_bundle_report.md
3. web_seed_urls_v6_1_candidates.csv
4. web_seed_urls_v6_1_prefetch_status.csv
5. web_seed_v6_1_prefetch_report.md
6. web_seed_v6_1_task_assignment.csv
7. knowledge_base_web_raw.csv
8. knowledge_base_web_rewritten.csv
9. rewrite_low_quality_log.csv
10. web_seed_v6_1_run_report.json
11. ai_review_audit.csv / ai_review_report_audit.json (if generated)
