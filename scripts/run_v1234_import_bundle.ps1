param(
  [string]$PythonExe = "python",
  [int]$Concurrency = 6,
  [int]$MaxChars = 1400,
  [int]$Overlap = 100,
  [ValidateSet("auto", "legacy", "skill")]
  [string]$FetcherMode = "auto"
)

$ErrorActionPreference = "Stop"

Write-Host "=== Step 1/5: Fetch V1 web seeds ===" -ForegroundColor Cyan
& $PythonExe scripts\web_ingest_pipeline.py `
  --manifest data_sources\web_seed_urls.csv `
  --output-dir artifacts\web_seed_v1_prefetch `
  --fetcher-mode $FetcherMode `
  --concurrency $Concurrency `
  --max-chars $MaxChars `
  --overlap $Overlap
if ($LASTEXITCODE -ne 0) { throw "V1 web fetch failed." }

Write-Host "=== Step 2/5: Fetch V2 web seeds ===" -ForegroundColor Cyan
& $PythonExe scripts\web_ingest_pipeline.py `
  --manifest data_sources\web_seed_urls_v2_candidates.csv `
  --output-dir artifacts\web_seed_v2_prefetch `
  --fetcher-mode $FetcherMode `
  --concurrency $Concurrency `
  --max-chars $MaxChars `
  --overlap $Overlap
if ($LASTEXITCODE -ne 0) { throw "V2 web fetch failed." }

Write-Host "=== Step 3/5: Fetch V3 web seeds ===" -ForegroundColor Cyan
& $PythonExe scripts\web_ingest_pipeline.py `
  --manifest data_sources\web_seed_urls_v3_candidates.csv `
  --output-dir artifacts\web_seed_v3_prefetch `
  --fetcher-mode $FetcherMode `
  --concurrency $Concurrency `
  --max-chars $MaxChars `
  --overlap $Overlap
if ($LASTEXITCODE -ne 0) { throw "V3 web fetch failed." }

Write-Host "=== Step 4/5: Generate V1/V2/V3 prefetch status ===" -ForegroundColor Cyan
& $PythonExe scripts\generate_web_prefetch_status.py `
  --manifest data_sources\web_seed_urls.csv `
  --fetch-results artifacts\web_seed_v1_prefetch\fetch_results.jsonl `
  --output data_sources\web_seed_urls_v1_prefetch_status.csv
if ($LASTEXITCODE -ne 0) { throw "Generate V1 prefetch status failed." }

& $PythonExe scripts\generate_web_prefetch_status.py `
  --manifest data_sources\web_seed_urls_v2_candidates.csv `
  --fetch-results artifacts\web_seed_v2_prefetch\fetch_results.jsonl `
  --output data_sources\web_seed_urls_v2_prefetch_status.csv
if ($LASTEXITCODE -ne 0) { throw "Generate V2 prefetch status failed." }

& $PythonExe scripts\generate_web_prefetch_status.py `
  --manifest data_sources\web_seed_urls_v3_candidates.csv `
  --fetch-results artifacts\web_seed_v3_prefetch\fetch_results.jsonl `
  --output data_sources\web_seed_urls_v3_prefetch_status.csv
if ($LASTEXITCODE -ne 0) { throw "Generate V3 prefetch status failed." }

Write-Host "=== Step 5/5: Build import-ready bundle ===" -ForegroundColor Cyan
& $PythonExe scripts\build_import_ready_bundle.py --output-dir artifacts\import_bundle_v1234
if ($LASTEXITCODE -ne 0) { throw "Build import-ready bundle failed." }

Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Green
Write-Host "Import CSV:"
Write-Host "  artifacts\import_bundle_v1234\knowledge_base_import_ready.csv"
Write-Host "Bundle report:"
Write-Host "  artifacts\import_bundle_v1234\import_bundle_report.md"

