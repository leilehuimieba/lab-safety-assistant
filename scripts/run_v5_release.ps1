param(
  [string]$PythonExe = "python",
  [switch]$SkipFetch = $false,
  [int]$Concurrency = 6,
  [int]$MaxChars = 1400,
  [int]$Overlap = 100
)

$ErrorActionPreference = "Stop"

$Manifest = "data_sources\web_seed_urls_v5_candidates.csv"
$PrefetchDir = "artifacts\web_seed_v5_prefetch"
$FetchResults = "$PrefetchDir\fetch_results.jsonl"
$KbCsv = "$PrefetchDir\knowledge_base_web.csv"
$StatusCsv = "data_sources\web_seed_urls_v5_prefetch_status.csv"
$BundleDir = "artifacts\import_bundle_v5"
$ReleaseDir = "release_exports\v5"
$V42Csv = "release_exports\v4.2\knowledge_base_import_ready.csv"
$CuratedCsv = "knowledge_base_curated.csv"

if (-not (Test-Path $Manifest)) { throw "Missing manifest: $Manifest" }
if (-not (Test-Path $V42Csv)) { throw "Missing base release CSV: $V42Csv" }
if (-not (Test-Path $CuratedCsv)) { throw "Missing curated CSV: $CuratedCsv" }

if (-not $SkipFetch) {
  Write-Host "=== Step 1/4: Fetch V5 web seeds ===" -ForegroundColor Cyan
  & $PythonExe scripts\web_ingest_pipeline.py `
    --manifest $Manifest `
    --output-dir $PrefetchDir `
    --fetcher-mode auto `
    --concurrency $Concurrency `
    --max-chars $MaxChars `
    --overlap $Overlap
  if ($LASTEXITCODE -ne 0) { throw "V5 web fetch failed." }
}

if (-not (Test-Path $FetchResults)) { throw "Missing fetch results: $FetchResults" }
if (-not (Test-Path $KbCsv)) { throw "Missing KB output: $KbCsv" }

Write-Host "=== Step 2/4: Generate V5 prefetch status ===" -ForegroundColor Cyan
& $PythonExe scripts\generate_web_prefetch_status.py `
  --manifest $Manifest `
  --fetch-results $FetchResults `
  --output $StatusCsv
if ($LASTEXITCODE -ne 0) { throw "Generate V5 prefetch status failed." }

Write-Host "=== Step 3/4: Build import-ready bundle (curated + v5 + v4.2) ===" -ForegroundColor Cyan
& $PythonExe scripts\build_import_ready_bundle.py `
  --output-dir $BundleDir `
  --source curated=$CuratedCsv `
  --source v5_web=$KbCsv `
  --source v4_2_release=$V42Csv
if ($LASTEXITCODE -ne 0) { throw "Build V5 import bundle failed." }

Write-Host "=== Step 4/4: Export V5 release directory ===" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null

Copy-Item "$BundleDir\knowledge_base_import_ready.csv" "$ReleaseDir\knowledge_base_import_ready.csv" -Force
Copy-Item "$BundleDir\import_bundle_report.json" "$ReleaseDir\import_bundle_report.json" -Force
Copy-Item "$BundleDir\import_bundle_report.md" "$ReleaseDir\import_bundle_report.md" -Force
Copy-Item $Manifest "$ReleaseDir\web_seed_urls_v5_candidates.csv" -Force
Copy-Item $StatusCsv "$ReleaseDir\web_seed_urls_v5_prefetch_status.csv" -Force
if (Test-Path "$PrefetchDir\run_report.json") {
  Copy-Item "$PrefetchDir\run_report.json" "$ReleaseDir\web_seed_v5_run_report.json" -Force
}
if (Test-Path "docs\pipeline\web_seed_v5_prefetch_report.md") {
  Copy-Item "docs\pipeline\web_seed_v5_prefetch_report.md" "$ReleaseDir\web_seed_v5_prefetch_report.md" -Force
}
if (Test-Path "data_sources\web_seed_v5_task_assignment.csv") {
  Copy-Item "data_sources\web_seed_v5_task_assignment.csv" "$ReleaseDir\web_seed_v5_task_assignment.csv" -Force
}

$rows = (Import-Csv "$ReleaseDir\knowledge_base_import_ready.csv" | Measure-Object).Count
$now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

$releaseNote = @"
# Release Export v5

- generated_at: $now
- import_ready_rows: $rows
- source_priority: curated > v5_web > v4_2_release

## Included files

1. knowledge_base_import_ready.csv
2. import_bundle_report.json / import_bundle_report.md
3. web_seed_urls_v5_candidates.csv
4. web_seed_urls_v5_prefetch_status.csv
5. web_seed_v5_run_report.json (if available)
6. web_seed_v5_prefetch_report.md (if available)
7. web_seed_v5_task_assignment.csv (if available)
"@
$releaseNote | Set-Content -Path "$ReleaseDir\README.md" -Encoding UTF8

Write-Host ""
Write-Host "=== V5 release pipeline done ===" -ForegroundColor Green
Write-Host "Import CSV: $ReleaseDir\knowledge_base_import_ready.csv"
Write-Host "Rows: $rows"
