param(
  [string]$InputRoot = "manual_sources",
  [string]$Manifest = "data_sources\manual_document_manifest.csv",
  [string]$PdfSpecialRules = "data_sources\pdf_special_rules.csv",
  [string]$OutputDir = "",
  [ValidateSet("auto", "off", "always")]
  [string]$PdfOcrMode = "auto",
  [int]$MaxChars = 1800,
  [int]$Overlap = 100,
  [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

function Resolve-RepoPath([string]$PathValue) {
  if ([System.IO.Path]::IsPathRooted($PathValue)) {
    return $PathValue
  }
  return (Join-Path $RepoRoot $PathValue)
}

$InputRoot = Resolve-RepoPath $InputRoot
$Manifest = Resolve-RepoPath $Manifest
$PdfSpecialRules = Resolve-RepoPath $PdfSpecialRules

if (-not $OutputDir) {
  $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
  $OutputDir = Join-Path $RepoRoot "artifacts\manual_kb_batch_$timestamp"
} else {
  $OutputDir = Resolve-RepoPath $OutputDir
}

if (-not (Test-Path $InputRoot)) {
  throw "InputRoot not found: $InputRoot. Put files under manual_sources\\inbox\\ first."
}
if (-not (Test-Path $Manifest)) {
  throw "Manifest not found: $Manifest"
}
$manifestLineCount = (Get-Content $Manifest | Where-Object { $_.Trim() -ne "" }).Count
if ($manifestLineCount -le 1) {
  throw "Manifest is empty: $Manifest. Add at least one row in manual_document_manifest.csv first."
}

$argsList = @(
  (Join-Path $RepoRoot "scripts\document_ingest_pipeline.py"),
  "--input-root", $InputRoot,
  "--manifest", $Manifest,
  "--only-manifest",
  "--pdf-special-rules", $PdfSpecialRules,
  "--output-dir", $OutputDir,
  "--pdf-ocr-mode", $PdfOcrMode,
  "--max-chars", "$MaxChars",
  "--overlap", "$Overlap"
)

Write-Host "=== Manual PDF Intake Start ===" -ForegroundColor Cyan
Write-Host "InputRoot: $InputRoot"
Write-Host "Manifest: $Manifest"
Write-Host "OutputDir: $OutputDir"
Write-Host ""

& $PythonExe @argsList
if ($LASTEXITCODE -ne 0) {
  throw "document_ingest_pipeline.py failed with exit code: $LASTEXITCODE"
}

$csvPath = Join-Path $OutputDir "knowledge_base_document.csv"
$runReport = Join-Path $OutputDir "run_report.json"
$skipped = Join-Path $OutputDir "skipped_files.json"

Write-Host ""
Write-Host "=== Completed ===" -ForegroundColor Green
Write-Host "1) CSV output: $csvPath"
Write-Host "2) Run report: $runReport"
Write-Host "3) Skipped files: $skipped"
Write-Host ""
Write-Host "Recommended next steps:"
Write-Host "- python scripts\quality_gate.py"
Write-Host "- python scripts\eval_smoke.py --generate-template"
