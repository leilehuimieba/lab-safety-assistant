param(
  [string]$PythonExe = "python",
  [string]$OpenAIBaseUrl = "https://api.tabcode.cc/openai",
  [string]$OpenAIApiKey = $env:OPENAI_API_KEY,
  [string]$OpenAIModel = "gpt-5.2-codex",
  [string]$OpenAIApi = "openai-responses",
  [switch]$OpenAIInsecureTls = $true,
  [int]$Concurrency = 6,
  [int]$MaxChars = 1400,
  [int]$Overlap = 100
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($OpenAIApiKey)) {
  throw "OpenAI API key is required. Pass -OpenAIApiKey or set OPENAI_API_KEY."
}

$RelinkReportDir = "artifacts\relink_v4_2"
$RepairRoot = "artifacts\v4_2_repair_round"
$BundleDir = "artifacts\import_bundle_v12342"
$ReleaseDir = "release_exports\v4.2"

Write-Host "=== Step 1/8: Apply V4.2 relink map ===" -ForegroundColor Cyan
& $PythonExe scripts\apply_official_relink.py `
  --map-csv data_sources\relink_official_map_v4_2.csv `
  --report-dir $RelinkReportDir `
  --tag-token official_relink_v4_2 `
  --v1-input data_sources\web_seed_urls_v1_1_candidates.csv `
  --v1-output data_sources\web_seed_urls_v1_2_candidates.csv `
  --v2-input data_sources\web_seed_urls_v2_1_candidates.csv `
  --v2-output data_sources\web_seed_urls_v2_2_candidates.csv `
  --v3-input data_sources\web_seed_urls_v3_1_candidates.csv `
  --v3-output data_sources\web_seed_urls_v3_2_candidates.csv
if ($LASTEXITCODE -ne 0) { throw "Apply V4.2 relink failed." }

Write-Host "=== Step 2/8: Fetch V1.2 web seeds ===" -ForegroundColor Cyan
& $PythonExe scripts\web_ingest_pipeline.py `
  --manifest data_sources\web_seed_urls_v1_2_candidates.csv `
  --output-dir artifacts\web_seed_v1_2_prefetch `
  --fetcher-mode auto `
  --concurrency $Concurrency `
  --max-chars $MaxChars `
  --overlap $Overlap
if ($LASTEXITCODE -ne 0) { throw "V1.2 web fetch failed." }

Write-Host "=== Step 3/8: Fetch V2.2 + V3.2 web seeds ===" -ForegroundColor Cyan
& $PythonExe scripts\web_ingest_pipeline.py `
  --manifest data_sources\web_seed_urls_v2_2_candidates.csv `
  --output-dir artifacts\web_seed_v2_2_prefetch `
  --fetcher-mode auto `
  --concurrency $Concurrency `
  --max-chars $MaxChars `
  --overlap $Overlap
if ($LASTEXITCODE -ne 0) { throw "V2.2 web fetch failed." }

& $PythonExe scripts\web_ingest_pipeline.py `
  --manifest data_sources\web_seed_urls_v3_2_candidates.csv `
  --output-dir artifacts\web_seed_v3_2_prefetch `
  --fetcher-mode auto `
  --concurrency $Concurrency `
  --max-chars $MaxChars `
  --overlap $Overlap
if ($LASTEXITCODE -ne 0) { throw "V3.2 web fetch failed." }

Write-Host "=== Step 4/8: Generate V1.2/V2.2/V3.2 prefetch status ===" -ForegroundColor Cyan
& $PythonExe scripts\generate_web_prefetch_status.py `
  --manifest data_sources\web_seed_urls_v1_2_candidates.csv `
  --fetch-results artifacts\web_seed_v1_2_prefetch\fetch_results.jsonl `
  --output data_sources\web_seed_urls_v1_2_prefetch_status.csv
if ($LASTEXITCODE -ne 0) { throw "Generate V1.2 status failed." }

& $PythonExe scripts\generate_web_prefetch_status.py `
  --manifest data_sources\web_seed_urls_v2_2_candidates.csv `
  --fetch-results artifacts\web_seed_v2_2_prefetch\fetch_results.jsonl `
  --output data_sources\web_seed_urls_v2_2_prefetch_status.csv
if ($LASTEXITCODE -ne 0) { throw "Generate V2.2 status failed." }

& $PythonExe scripts\generate_web_prefetch_status.py `
  --manifest data_sources\web_seed_urls_v3_2_candidates.csv `
  --fetch-results artifacts\web_seed_v3_2_prefetch\fetch_results.jsonl `
  --output data_sources\web_seed_urls_v3_2_prefetch_status.csv
if ($LASTEXITCODE -ne 0) { throw "Generate V3.2 status failed." }

Write-Host "=== Step 5/8: Build relink success candidates (V4.2 targets) ===" -ForegroundColor Cyan
& $PythonExe scripts\build_relink_success_candidates.py `
  --map-csv data_sources\relink_official_map_v4_2.csv `
  --status-csv data_sources\web_seed_urls_v1_2_prefetch_status.csv `
  --status-csv data_sources\web_seed_urls_v2_2_prefetch_status.csv `
  --status-csv data_sources\web_seed_urls_v3_2_prefetch_status.csv `
  --kb-csv artifacts\web_seed_v1_2_prefetch\knowledge_base_web.csv `
  --kb-csv artifacts\web_seed_v2_2_prefetch\knowledge_base_web.csv `
  --kb-csv artifacts\web_seed_v3_2_prefetch\knowledge_base_web.csv `
  --output-csv artifacts\relink_v4_2\relink_success_kb_candidates.csv `
  --id-status-csv artifacts\relink_v4_2\relink_success_ids.csv
if ($LASTEXITCODE -ne 0) { throw "Build relink success candidates failed." }

Write-Host "=== Step 6/8: AI rewrite + recheck (V4.2) ===" -ForegroundColor Cyan
$repairArgs = @(
  "scripts\run_v4_repair_round.py",
  "--repo-root", ".",
  "--input-csv", "artifacts\relink_v4_2\relink_success_kb_candidates.csv",
  "--output-root", $RepairRoot,
  "--audit-min-score", "72",
  "--recheck-min-score", "82",
  "--openai-base-url", $OpenAIBaseUrl,
  "--openai-api-key", $OpenAIApiKey,
  "--openai-model", $OpenAIModel,
  "--openai-api", $OpenAIApi,
  "--openai-timeout", "90"
)
if ($OpenAIInsecureTls) {
  $repairArgs += "--openai-insecure-tls"
}

& $PythonExe @repairArgs
if ($LASTEXITCODE -ne 0) { throw "V4.2 repair round failed." }

$latestRepairRun = Get-ChildItem $RepairRoot -Directory | Where-Object { $_.Name -like "run_*" } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $latestRepairRun) { throw "No repair run directory found in $RepairRoot." }
$v42RecheckPass = Join-Path $latestRepairRun.FullName "second_recheck\knowledge_base_recheck_pass.csv"
if (-not (Test-Path $v42RecheckPass)) { throw "Missing V4.2 recheck pass CSV: $v42RecheckPass" }

Write-Host "=== Step 7/8: Build V1~V4.2 import bundle ===" -ForegroundColor Cyan
& $PythonExe scripts\build_import_ready_bundle.py `
  --output-dir $BundleDir `
  --source curated=knowledge_base_curated.csv `
  --source v4_2_recheck=$v42RecheckPass `
  --source v4_1_recheck=artifacts/v4_1_repair_round/run_20260327_201226/second_recheck/knowledge_base_recheck_pass.csv `
  --source v4_pass=artifacts/v4_repair_round/run_20260327_190336/second_recheck/knowledge_base_recheck_pass.csv `
  --source v3_2_web=artifacts/web_seed_v3_2_prefetch/knowledge_base_web.csv `
  --source v2_2_web=artifacts/web_seed_v2_2_prefetch/knowledge_base_web.csv `
  --source v1_2_web=artifacts/web_seed_v1_2_prefetch/knowledge_base_web.csv `
  --source v3_unified=artifacts/dify_kb_batch_v3/knowledge_base_unified.csv `
  --source v2_unified=artifacts/dify_kb_batch_v2/knowledge_base_unified.csv `
  --source v1_unified=artifacts/dify_kb_batch_v1/knowledge_base_unified.csv
if ($LASTEXITCODE -ne 0) { throw "Build V1~V4.2 bundle failed." }

Write-Host "=== Step 8/8: Export release files to $ReleaseDir ===" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null

Copy-Item "$BundleDir\knowledge_base_import_ready.csv" "$ReleaseDir\knowledge_base_import_ready.csv" -Force
Copy-Item "$BundleDir\import_bundle_report.json" "$ReleaseDir\import_bundle_report.json" -Force
Copy-Item "$BundleDir\import_bundle_report.md" "$ReleaseDir\import_bundle_report.md" -Force
Copy-Item "data_sources\relink_official_map_v4_2.csv" "$ReleaseDir\relink_official_map_v4_2.csv" -Force
Copy-Item "data_sources\web_seed_urls_v1_2_candidates.csv" "$ReleaseDir\web_seed_urls_v1_2_candidates.csv" -Force
Copy-Item "data_sources\web_seed_urls_v2_2_candidates.csv" "$ReleaseDir\web_seed_urls_v2_2_candidates.csv" -Force
Copy-Item "data_sources\web_seed_urls_v3_2_candidates.csv" "$ReleaseDir\web_seed_urls_v3_2_candidates.csv" -Force
Copy-Item "data_sources\web_seed_urls_v1_2_prefetch_status.csv" "$ReleaseDir\web_seed_urls_v1_2_prefetch_status.csv" -Force
Copy-Item "data_sources\web_seed_urls_v2_2_prefetch_status.csv" "$ReleaseDir\web_seed_urls_v2_2_prefetch_status.csv" -Force
Copy-Item "data_sources\web_seed_urls_v3_2_prefetch_status.csv" "$ReleaseDir\web_seed_urls_v3_2_prefetch_status.csv" -Force
Copy-Item "$RelinkReportDir\official_relink_summary.md" "$ReleaseDir\official_relink_summary.md" -Force
Copy-Item "$RelinkReportDir\official_relink_details.csv" "$ReleaseDir\official_relink_details.csv" -Force
Copy-Item "$RelinkReportDir\relink_success_ids.csv" "$ReleaseDir\relink_success_ids.csv" -Force
Copy-Item "$RelinkReportDir\relink_success_kb_candidates.csv" "$ReleaseDir\relink_success_kb_candidates.csv" -Force
Copy-Item (Join-Path $latestRepairRun.FullName "repair_round_report.json") "$ReleaseDir\repair_round_report.json" -Force
Copy-Item (Join-Path $latestRepairRun.FullName "repair_round_report.md") "$ReleaseDir\repair_round_report.md" -Force
Copy-Item $v42RecheckPass "$ReleaseDir\knowledge_base_recheck_pass_v4_2.csv" -Force

$releaseNote = @"
# Release Export v4.2

- generated_at: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
- repair_run: $($latestRepairRun.FullName)
- bundle_dir: $BundleDir
- release_dir: $ReleaseDir

## Included files

1. knowledge_base_import_ready.csv
2. import_bundle_report.json / import_bundle_report.md
3. relink_official_map_v4_2.csv
4. web_seed_urls_v1_2/v2_2/v3_2 candidates + prefetch_status
5. official_relink_summary.md + official_relink_details.csv
6. relink_success_ids.csv + relink_success_kb_candidates.csv
7. repair_round_report.json / repair_round_report.md
8. knowledge_base_recheck_pass_v4_2.csv
"@
$releaseNote | Set-Content -Path "$ReleaseDir\README.md" -Encoding UTF8

Write-Host ""
Write-Host "=== V4.2 release pipeline done ===" -ForegroundColor Green
Write-Host "Repair run: $($latestRepairRun.FullName)"
Write-Host "Import CSV: $ReleaseDir\knowledge_base_import_ready.csv"
