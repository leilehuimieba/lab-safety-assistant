param(
  [string]$PythonExe = "python",
  [string]$DifyBaseUrl = "http://localhost:8080",
  [string]$DatasetId = "",
  [string]$DatasetApiKey = "",
  [string]$DatasetName = "实验室安全知识库",
  [string]$AppApiKey = "",
  [int]$EvalLimit = 20,
  [switch]$SkipHealthGate = $false,
  [switch]$SkipEmbeddingHealthCheck = $true,
  [switch]$AllowChatTimeoutPass = $false,
  [double]$HealthPreflightTimeout = 8.0,
  [double]$HealthChatPreflightTimeout = 20.0,
  [int]$RetryOnTimeout = 1,
  [switch]$WaitIndexing = $true,
  [int]$WaitIndexingTimeoutSec = 1800,
  [switch]$SkipImport = $false,
  [switch]$AutoDetectDataset = $true,
  [switch]$AutoProvisionDatasetToken = $true,
  [switch]$AutoFetchAppKeyFromDb = $true,
  [string]$DbContainer = "docker-db_postgres-1",
  [string]$DbUser = "postgres",
  [string]$DbName = "dify"
)

$ErrorActionPreference = "Stop"

function Get-LatestAppTokenFromDb {
  param(
    [string]$Container,
    [string]$User,
    [string]$Database
  )
  $sql = "select token from api_tokens where type='app' order by created_at desc limit 1;"
  $token = docker exec $Container psql -U $User -d $Database -t -A -c $sql
  return ($token | Out-String).Trim()
}

function Test-DockerApiAvailable {
  try {
    docker version --format "{{.Server.Version}}" *> $null
    return ($LASTEXITCODE -eq 0)
  }
  catch {
    return $false
  }
}

$CsvPath = "release_exports\v7\knowledge_base_import_ready.csv"
if (-not (Test-Path $CsvPath)) {
  throw "Missing CSV: $CsvPath"
}

if (-not $AppApiKey) {
  $AppApiKey = $env:DIFY_APP_API_KEY
}

if (-not $AppApiKey -and $AutoFetchAppKeyFromDb) {
  if (Test-DockerApiAvailable) {
    $AppApiKey = Get-LatestAppTokenFromDb -Container $DbContainer -User $DbUser -Database $DbName
  } else {
    Write-Host "Docker API unavailable, skip auto-fetch app key from DB." -ForegroundColor Yellow
  }
}

if (-not $SkipHealthGate) {
  if (-not $AppApiKey) {
    throw "Health gate enabled but AppApiKey is missing. Set DIFY_APP_API_KEY env or pass -AppApiKey."
  }
  Write-Host "=== Precheck: Live health gate (Dify) ===" -ForegroundColor Cyan
  $healthArgs = @(
    "scripts\check_live_eval_health.py",
    "--dify-base-url", $DifyBaseUrl,
    "--dify-app-key", $AppApiKey,
    "--response-mode", "streaming",
    "--preflight-timeout", "$HealthPreflightTimeout",
    "--chat-preflight-timeout", "$HealthChatPreflightTimeout",
    "--output-dir", "artifacts/eval_health_gate_v7"
  )
  if ($SkipEmbeddingHealthCheck) {
    $healthArgs += "--skip-embedding-check"
  }
  if ($AllowChatTimeoutPass) {
    $healthArgs += "--allow-chat-timeout-pass"
  }
  & $PythonExe @healthArgs
  if ($LASTEXITCODE -ne 0) {
    throw "Live health gate failed. Abort v7 demo chain."
  }
}

if (-not $SkipImport) {
  Write-Host "=== Step 1/2: Import v7 CSV into Dify Dataset ===" -ForegroundColor Cyan
  $importArgs = @(
    "scripts\import_csv_to_dify_dataset.py",
    "--csv", $CsvPath,
    "--base-url", $DifyBaseUrl,
    "--skip-existing",
    "--report-json", "artifacts\dify_import_v7\import_report.json",
    "--report-md", "docs\eval\dify_import_v7_report.md",
    "--db-container", $DbContainer,
    "--db-user", $DbUser,
    "--db-name", $DbName,
    "--dataset-name", $DatasetName
  )
  if ($DatasetId) { $importArgs += @("--dataset-id", $DatasetId) }
  if ($DatasetApiKey) { $importArgs += @("--dataset-api-key", $DatasetApiKey) }
  if ($AutoDetectDataset) { $importArgs += "--auto-detect-dataset" }
  if ($AutoProvisionDatasetToken) { $importArgs += "--auto-provision-token" }
  if ($WaitIndexing) {
    $importArgs += @("--wait-indexing", "--wait-timeout-sec", "$WaitIndexingTimeoutSec")
  }
  & $PythonExe @importArgs
  if ($LASTEXITCODE -ne 0) { throw "Dify dataset import failed." }
}

if (-not $AppApiKey) {
  throw "Missing app api key. Set DIFY_APP_API_KEY env or pass -AppApiKey."
}

Write-Host "=== Step 2/2: Run live 20-question regression via Dify App API ===" -ForegroundColor Cyan
& $PythonExe scripts\eval_smoke.py `
  --use-dify `
  --dify-base-url $DifyBaseUrl `
  --dify-app-key $AppApiKey `
  --dify-response-mode streaming `
  --dify-timeout 180 `
  --retry-on-timeout $RetryOnTimeout `
  --concurrency 1 `
  --limit $EvalLimit `
  --output-dir artifacts/eval_smoke_v7_demo_chain
if ($LASTEXITCODE -ne 0) { throw "Live regression failed." }

Write-Host ""
Write-Host "=== v7 demo chain completed ===" -ForegroundColor Green
Write-Host "- Import report: artifacts\\dify_import_v7\\import_report.json"
Write-Host "- Eval output root: artifacts\\eval_smoke_v7_demo_chain"
