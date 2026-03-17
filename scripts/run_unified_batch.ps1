param(
  [string]$DocumentInputRoot = "D:\workspace\data",
  [string]$OutputDir = "",
  [string]$DocumentManifest = "data_sources\document_manifest.csv",
  [string]$PdfSpecialRules = "data_sources\pdf_special_rules.csv",
  [switch]$SkipWeb,
  [ValidateSet("auto", "off", "always")]
  [string]$PdfOcrMode = "auto",
  [int]$DocumentMaxChars = 1800,
  [int]$DocumentOverlap = 100,
  [int]$WebMaxChars = 1400,
  [int]$WebOverlap = 100,
  [string]$WebManifest = "data_sources\web_seed_urls.csv",
  [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

if (-not $OutputDir) {
  $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
  $OutputDir = "artifacts\dify_kb_batch_$timestamp"
}

$argsList = @(
  "scripts\unified_kb_pipeline.py",
  "--output-dir", $OutputDir,
  "--document-input-root", $DocumentInputRoot,
  "--document-manifest", $DocumentManifest,
  "--document-only-manifest",
  "--document-pdf-special-rules", $PdfSpecialRules,
  "--pdf-ocr-mode", $PdfOcrMode,
  "--document-max-chars", "$DocumentMaxChars",
  "--document-overlap", "$DocumentOverlap"
)

if ($SkipWeb) {
  $argsList += "--skip-web"
}
else {
  $argsList += @(
    "--web-manifest", $WebManifest,
    "--web-max-chars", "$WebMaxChars",
    "--web-overlap", "$WebOverlap"
  )
}

Write-Host "=== Unified KB Batch Start ===" -ForegroundColor Cyan
Write-Host "OutputDir: $OutputDir"
if ($SkipWeb) {
  Write-Host "Web: skipped"
} else {
  Write-Host "Web: enabled"
}
Write-Host ""

& $PythonExe @argsList
if ($LASTEXITCODE -ne 0) {
  throw "unified_kb_pipeline.py failed with exit code: $LASTEXITCODE"
}

$csvPath = Join-Path $OutputDir "knowledge_base_unified.csv"
$runReport = Join-Path $OutputDir "run_report.json"

Write-Host ""
Write-Host "=== Completed ===" -ForegroundColor Green
Write-Host "1) CSV output: $csvPath"
Write-Host "2) Run report: $runReport"
Write-Host ""
Write-Host "Recommended next steps:"
Write-Host "- python scripts\quality_gate.py"
Write-Host "- pytest"
Write-Host "- python scripts\eval_smoke.py --use-dify --limit 20"
