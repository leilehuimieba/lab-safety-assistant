param(
  [string]$PythonExe = "python",
  [switch]$SkipFetch = $false,
  [int]$Concurrency = 6,
  [int]$MaxChars = 1400,
  [int]$Overlap = 100,
  [double]$LowQualityThreshold = 0.70,
  [string]$SkillScript = "skills\web-content-fetcher\scripts\fetch_web_content.py",
  [string]$SkillProviders = "jina,scrapling,direct",
  [int]$FetchTimeout = 30,
  [int]$FetchMaxChars = 30000
)

$ErrorActionPreference = "Stop"

$Manifest = "data_sources\web_seed_urls_v8_1_candidates.csv"
$PrefetchDir = "artifacts\web_seed_v8_1_prefetch"
$FetchResults = "$PrefetchDir\fetch_results.jsonl"
$KbCsv = "$PrefetchDir\knowledge_base_web.csv"
$KbRewrittenCsv = "$PrefetchDir\knowledge_base_web_rewritten.csv"
$RewriteLogCsv = "$PrefetchDir\rewrite_log.csv"
$StatusCsv = "data_sources\web_seed_urls_v8_1_prefetch_status.csv"
$ReportMd = "docs\pipeline\web_seed_v8_1_prefetch_report.md"
$AssignmentCsv = "data_sources\web_seed_v8_1_task_assignment.csv"
$BundleDir = "artifacts\import_bundle_v8_1"
$ReleaseDir = "release_exports\v8.1"
$CuratedCsv = "knowledge_base_curated.csv"
$BaseReleaseCsv = "release_exports\v7\knowledge_base_import_ready.csv"

if (-not (Test-Path $Manifest)) { throw "Missing manifest: $Manifest" }
if (-not (Test-Path $CuratedCsv)) { throw "Missing curated CSV: $CuratedCsv" }

if (-not $SkipFetch) {
  Write-Host "=== Step 1/6: Fetch V8.1 web seeds (skill mode) ===" -ForegroundColor Cyan
  & $PythonExe scripts\web_ingest_pipeline.py `
    --manifest $Manifest `
    --output-dir $PrefetchDir `
    --fetcher-mode skill `
    --skill-script $SkillScript `
    --skill-providers $SkillProviders `
    --concurrency $Concurrency `
    --max-chars $MaxChars `
    --overlap $Overlap `
    --fetch-timeout $FetchTimeout `
    --fetch-max-chars $FetchMaxChars
  if ($LASTEXITCODE -ne 0) { throw "V8.1 web fetch failed." }
}

if (-not (Test-Path $FetchResults)) { throw "Missing fetch results: $FetchResults" }
if (-not (Test-Path $KbCsv)) { throw "Missing KB output: $KbCsv" }

Write-Host "=== Step 2/6: Generate V8.1 prefetch status ===" -ForegroundColor Cyan
& $PythonExe scripts\generate_web_prefetch_status.py `
  --manifest $Manifest `
  --fetch-results $FetchResults `
  --output $StatusCsv
if ($LASTEXITCODE -ne 0) { throw "Generate V8.1 prefetch status failed." }

Write-Host "=== Step 3/6: Generate report and task assignment ===" -ForegroundColor Cyan
& $PythonExe scripts\generate_web_prefetch_report.py `
  --status-csv $StatusCsv `
  --output-report $ReportMd `
  --output-assignment $AssignmentCsv `
  --low-quality-threshold $LowQualityThreshold `
  --batch-name "web_seed_v8_1"
if ($LASTEXITCODE -ne 0) { throw "Generate V8.1 prefetch report failed." }

Write-Host "=== Step 4/6: Rewrite low-quality rows ===" -ForegroundColor Cyan
& $PythonExe scripts\rewrite_low_quality_rows.py `
  --input-csv $KbCsv `
  --status-csv $StatusCsv `
  --output-csv $KbRewrittenCsv `
  --log-csv $RewriteLogCsv `
  --low-quality-threshold $LowQualityThreshold
if ($LASTEXITCODE -ne 0) { throw "Rewrite low-quality rows failed." }

Write-Host "=== Step 5/6: Build import-ready bundle (curated + v8.1 + previous v7) ===" -ForegroundColor Cyan
$buildArgs = @(
  "scripts\build_import_ready_bundle.py",
  "--output-dir", $BundleDir,
  "--source", "curated=$CuratedCsv",
  "--source", "v8_1_web_rewritten=$KbRewrittenCsv"
)
if (Test-Path $BaseReleaseCsv) {
  $buildArgs += @("--source", "v7_previous_release=$BaseReleaseCsv")
}
& $PythonExe @buildArgs
if ($LASTEXITCODE -ne 0) { throw "Build V8.1 import bundle failed." }

Write-Host "=== Step 6/6: Export V8.1 release directory ===" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null

Copy-Item "$BundleDir\knowledge_base_import_ready.csv" "$ReleaseDir\knowledge_base_import_ready.csv" -Force
Copy-Item "$BundleDir\import_bundle_report.json" "$ReleaseDir\import_bundle_report.json" -Force
Copy-Item "$BundleDir\import_bundle_report.md" "$ReleaseDir\import_bundle_report.md" -Force
Copy-Item $Manifest "$ReleaseDir\web_seed_urls_v8_1_candidates.csv" -Force
Copy-Item $StatusCsv "$ReleaseDir\web_seed_urls_v8_1_prefetch_status.csv" -Force
Copy-Item $AssignmentCsv "$ReleaseDir\web_seed_v8_1_task_assignment.csv" -Force
Copy-Item $ReportMd "$ReleaseDir\web_seed_v8_1_prefetch_report.md" -Force
Copy-Item $KbCsv "$ReleaseDir\knowledge_base_web_v8_1.csv" -Force
Copy-Item $KbRewrittenCsv "$ReleaseDir\knowledge_base_web_v8_1_rewritten.csv" -Force
Copy-Item $RewriteLogCsv "$ReleaseDir\rewrite_log_v8_1.csv" -Force
if (Test-Path "$PrefetchDir\run_report.json") {
  Copy-Item "$PrefetchDir\run_report.json" "$ReleaseDir\web_seed_v8_1_run_report.json" -Force
}

$statusRows = Import-Csv $StatusCsv
$total = $statusRows.Count
$ok = ($statusRows | Where-Object { $_.status -eq "ok" }).Count
$blocked = ($statusRows | Where-Object { $_.status -eq "blocked" }).Count
$failed = $total - $ok - $blocked
$low = ($statusRows | Where-Object {
  $score = 0.0
  [double]::TryParse($_.quality_score, [ref]$score) | Out-Null
  $score -lt $LowQualityThreshold
}).Count
$rows = (Import-Csv "$ReleaseDir\knowledge_base_import_ready.csv" | Measure-Object).Count
$now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

$releaseNote = @"
# Release Export v8.1

- generated_at: $now
- import_ready_rows: $rows
- prefetch_total: $total
- prefetch_ok: $ok
- prefetch_blocked: $blocked
- prefetch_failed: $failed
- low_quality_before_rewrite: $low
- fetch_mode: skill($SkillProviders)
- source_priority: curated > v8_1_web_rewritten > v7_previous_release(optional)

## Included files

1. knowledge_base_import_ready.csv
2. import_bundle_report.json / import_bundle_report.md
3. web_seed_urls_v8_1_candidates.csv
4. web_seed_urls_v8_1_prefetch_status.csv
5. web_seed_v8_1_prefetch_report.md
6. web_seed_v8_1_task_assignment.csv
7. knowledge_base_web_v8_1.csv
8. knowledge_base_web_v8_1_rewritten.csv
9. rewrite_log_v8_1.csv
10. web_seed_v8_1_run_report.json (if available)
"@
$releaseNote | Set-Content -Path "$ReleaseDir\README.md" -Encoding UTF8

Write-Host ""
Write-Host "=== V8.1 release pipeline done ===" -ForegroundColor Green
Write-Host "Import CSV: $ReleaseDir\knowledge_base_import_ready.csv"
Write-Host "Rows: $rows"
Write-Host "Prefetch OK: $ok/$total"
