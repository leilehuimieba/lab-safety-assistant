param(
  [string]$RepoRoot = ".",
  [string]$OutputRoot = "artifacts\\eval_release_oneclick",
  [string]$WorkflowId = "",
  [string]$PrimaryModel = "gpt-5.2-codex",
  [string]$FallbackModel = "MiniMax-M2.5",
  [int]$Limit = 20,
  [double]$DifyTimeout = 60,
  [int]$CanaryLimit = 3,
  [double]$CanaryTimeout = 20,
  [double]$CanaryTimeoutFailoverThreshold = 1.0,
  [int]$FailoverFailStreakThreshold = 2,
  [double]$FailoverMaxAgeHours = 72,
  [int]$FailoverDays = 7,
  [switch]$SkipFailoverEval,
  [switch]$SkipGate,
  [switch]$SkipReleasePolicyCheck,
  [string]$ReleasePolicyProfile = "demo",
  [switch]$ReleasePolicyRunSecondary,
  [string]$ReleasePolicySecondaryProfile = "prod",
  [switch]$ReleasePolicyEnforceSecondary,
  [switch]$ReleasePolicyStrict,
  [switch]$SkipHealthCheck,
  [switch]$HealthAllowChatTimeoutPass,
  [switch]$SkipCanary,
  [switch]$AllowSkipLive,
  [switch]$RestorePrimaryAfterRun,
  [switch]$FailoverAllowDegraded,
  [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
$repoPath = Resolve-Path $RepoRoot

$argsList = @(
  "scripts\\run_eval_release_oneclick.py",
  "--repo-root", "$repoPath",
  "--output-root", $OutputRoot,
  "--primary-model", $PrimaryModel,
  "--fallback-model", $FallbackModel,
  "--limit", "$Limit",
  "--dify-timeout", "$DifyTimeout",
  "--canary-limit", "$CanaryLimit",
  "--canary-timeout", "$CanaryTimeout",
  "--canary-timeout-failover-threshold", "$CanaryTimeoutFailoverThreshold",
  "--failover-fail-streak-threshold", "$FailoverFailStreakThreshold",
  "--failover-max-age-hours", "$FailoverMaxAgeHours",
  "--failover-days", "$FailoverDays",
  "--release-policy-profile", $ReleasePolicyProfile,
  "--release-policy-secondary-profile", $ReleasePolicySecondaryProfile
)

if ($WorkflowId) { $argsList += @("--workflow-id", $WorkflowId) }
if ($SkipFailoverEval) { $argsList += "--skip-failover-eval" }
if ($SkipGate) { $argsList += "--skip-gate" }
if ($SkipReleasePolicyCheck) { $argsList += "--skip-release-policy-check" }
if ($ReleasePolicyRunSecondary) { $argsList += "--release-policy-run-secondary" }
if ($ReleasePolicyEnforceSecondary) { $argsList += "--release-policy-enforce-secondary" }
if ($ReleasePolicyStrict) { $argsList += "--release-policy-strict" }
if ($SkipHealthCheck) { $argsList += "--skip-health-check" }
if ($HealthAllowChatTimeoutPass) { $argsList += "--health-allow-chat-timeout-pass" }
if ($SkipCanary) { $argsList += "--skip-canary" }
if ($AllowSkipLive) { $argsList += "--allow-skip-live" }
if ($RestorePrimaryAfterRun) { $argsList += "--restore-primary-after-run" }
if ($FailoverAllowDegraded) { $argsList += "--failover-allow-degraded" }

Write-Host "=== Eval Release One-Click Start ===" -ForegroundColor Cyan
Write-Host "RepoRoot: $repoPath"
Write-Host "OutputRoot: $OutputRoot"
if (-not $SkipFailoverEval) {
  Write-Host "WorkflowId: $WorkflowId"
}
Write-Host ""

Push-Location $repoPath
try {
  & $PythonExe @argsList
  $exitCode = $LASTEXITCODE
}
finally {
  Pop-Location
}

if ($exitCode -eq 0) {
  Write-Host ""
  Write-Host "=== Eval Release One-Click Done (PASS) ===" -ForegroundColor Green
  exit 0
}

if ($exitCode -eq 2) {
  Write-Host ""
  Write-Host "=== Eval Release One-Click Done (BLOCKED BY GATE) ===" -ForegroundColor Yellow
  exit 2
}

throw "run_eval_release_oneclick.py failed with exit code: $exitCode"
