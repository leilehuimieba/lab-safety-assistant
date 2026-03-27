param(
  [string]$RepoRoot = ".",
  [string]$OutputRoot = "artifacts\\ai_oneclick",
  [string]$InputCsv = "",
  [string]$DocumentInputRoot = "..\\data",
  [string]$DocumentManifest = "data_sources\\document_manifest.csv",
  [string]$PdfSpecialRules = "data_sources\\pdf_special_rules.csv",
  [ValidateSet("auto", "off", "always")]
  [string]$PdfOcrMode = "auto",
  [switch]$SkipWeb,
  [string]$WebManifest = "data_sources\\web_seed_urls.csv",
  [ValidateSet("auto", "legacy", "skill")]
  [string]$WebFetcherMode = "auto",
  [string]$WebSkillScript = "",
  [string]$WebSkillProviders = "jina,scrapling,direct",
  [int]$AuditMinScore = 72,
  [int]$RecheckMinScore = 82,
  [int]$ReviewLimit = 0,
  [switch]$StrictHighRisk,
  [string]$MergeInto = "knowledge_base_curated.csv",
  [switch]$SkipMerge,
  [switch]$SkipQualityGate,
  [switch]$SkipEvalRegression,
  [switch]$AllowSkipLiveEval,
  [int]$EvalLimit = 0,
  [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
$repoPath = Resolve-Path $RepoRoot

$argsList = @(
  "scripts\\run_ai_oneclick_pipeline.py",
  "--repo-root", "$repoPath",
  "--output-root", $OutputRoot,
  "--document-input-root", $DocumentInputRoot,
  "--document-manifest", $DocumentManifest,
  "--document-pdf-special-rules", $PdfSpecialRules,
  "--pdf-ocr-mode", $PdfOcrMode,
  "--web-manifest", $WebManifest,
  "--web-fetcher-mode", $WebFetcherMode,
  "--web-skill-providers", $WebSkillProviders,
  "--audit-min-score", "$AuditMinScore",
  "--recheck-min-score", "$RecheckMinScore",
  "--review-limit", "$ReviewLimit",
  "--merge-into", $MergeInto
)

if ($InputCsv) { $argsList += @("--input-csv", $InputCsv) }
if ($SkipWeb) { $argsList += "--skip-web" }
if ($WebSkillScript) { $argsList += @("--web-skill-script", $WebSkillScript) }
if ($StrictHighRisk) { $argsList += "--strict-high-risk" }
if ($SkipMerge) { $argsList += "--skip-merge" }
if ($SkipQualityGate) { $argsList += "--skip-quality-gate" }
if ($SkipEvalRegression) { $argsList += "--skip-eval-regression" }
if ($AllowSkipLiveEval) { $argsList += "--allow-skip-live-eval" }
if ($EvalLimit -gt 0) { $argsList += @("--eval-limit", "$EvalLimit") }

Write-Host "=== AI One-Click Pipeline Start ===" -ForegroundColor Cyan
Write-Host "RepoRoot: $repoPath"
Write-Host "OutputRoot: $OutputRoot"
Write-Host "WebFetcherMode: $WebFetcherMode"
Write-Host ""

Push-Location $repoPath
try {
  & $PythonExe @argsList
  if ($LASTEXITCODE -ne 0) {
    throw "run_ai_oneclick_pipeline.py failed with exit code: $LASTEXITCODE"
  }
}
finally {
  Pop-Location
}

Write-Host ""
Write-Host "=== AI One-Click Pipeline Done ===" -ForegroundColor Green

