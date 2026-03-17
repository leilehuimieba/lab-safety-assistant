param(
  [string]$InputRoot = "D:\workspace\data",
  [string]$OutputDir = "",
  [int]$Limit = 0,
  [ValidateSet("auto", "off", "always")]
  [string]$OcrReviewMode = "auto",
  [int]$OcrReviewLimit = 10,
  [double]$OcrReviewThreshold = 0.2,
  [string]$PdfSpecialRules = "data_sources\pdf_special_rules.csv",
  [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

if (-not $OutputDir) {
  $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
  $OutputDir = "artifacts\pdf_validation_$timestamp"
}

Write-Host "=== PDF Batch Validation Start ===" -ForegroundColor Cyan
Write-Host "InputRoot: $InputRoot"
Write-Host "OutputDir: $OutputDir"
Write-Host "OcrMode  : $OcrReviewMode"
Write-Host ""

& $PythonExe scripts\pdf_batch_validation.py `
  --input-root $InputRoot `
  --output-dir $OutputDir `
  --limit $Limit `
  --ocr-review-mode $OcrReviewMode `
  --ocr-review-limit $OcrReviewLimit `
  --ocr-review-threshold $OcrReviewThreshold `
  --pdf-special-rules $PdfSpecialRules

if ($LASTEXITCODE -ne 0) {
  throw "pdf_batch_validation.py failed with exit code: $LASTEXITCODE"
}

$manualSheet = Join-Path $OutputDir "manual_review_sheet.csv"
$reportJson = Join-Path $OutputDir "validation_report.json"

Write-Host ""
Write-Host "=== Completed ===" -ForegroundColor Green
Write-Host "1) Manual sheet: $manualSheet"
Write-Host "2) Report json : $reportJson"
Write-Host ""
Write-Host "Manual review checklist:"
Write-Host "- Check manual_need_ocr (set yes when text is unreadable)"
Write-Host "- Check body_start_page points to actual body pages"
Write-Host "- Check cover/toc pages are skipped correctly"
Write-Host "- Set manual_review_status=done before formal batch"
