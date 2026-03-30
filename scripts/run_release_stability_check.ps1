param(
  [string]$RepoRoot = ".",
  [int]$Rounds = 3,
  [int]$IntervalSec = 30,
  [string]$WorkflowId = "",
  [string]$PrimaryModel = "gpt-5.2-codex",
  [string]$FallbackModel = "MiniMax-M2.5",
  [string]$DifyBaseUrl = "",
  [string]$DifyAppKey = "",
  [int]$Limit = 20,
  [double]$DifyTimeout = 180,
  [int]$EvalConcurrency = 1,
  [int]$RetryOnTimeout = 1,
  [switch]$SkipHealthCheck,
  [switch]$SkipCanary,
  [switch]$SkipFailoverEval,
  [int]$FailoverDays = 1,
  [int]$FailoverFailStreakThreshold = 2,
  [string]$ReleasePolicyProfile = "demo",
  [switch]$ReleasePolicyRunSecondary = $true,
  [string]$ReleasePolicySecondaryProfile = "prod",
  [switch]$ReleasePolicyEnforceSecondary = $true,
  [switch]$ReleasePolicyStrict = $true,
  [switch]$ContinueOnFail
)

$ErrorActionPreference = "Stop"

$argsList = @(
  "scripts/release/run_release_stability_check.py",
  "--repo-root", $RepoRoot,
  "--rounds", "$Rounds",
  "--interval-sec", "$IntervalSec",
  "--primary-model", $PrimaryModel,
  "--fallback-model", $FallbackModel,
  "--limit", "$Limit",
  "--dify-timeout", "$DifyTimeout",
  "--eval-concurrency", "$EvalConcurrency",
  "--retry-on-timeout", "$RetryOnTimeout",
  "--failover-days", "$FailoverDays",
  "--failover-fail-streak-threshold", "$FailoverFailStreakThreshold",
  "--release-policy-profile", $ReleasePolicyProfile
)

if ($WorkflowId) { $argsList += @("--workflow-id", $WorkflowId) }
if ($DifyBaseUrl) { $argsList += @("--dify-base-url", $DifyBaseUrl) }
if ($DifyAppKey) { $argsList += @("--dify-app-key", $DifyAppKey) }

if ($SkipHealthCheck) { $argsList += "--skip-health-check" }
if ($SkipCanary) { $argsList += "--skip-canary" }
if ($SkipFailoverEval) { $argsList += "--skip-failover-eval" }
if ($ContinueOnFail) { $argsList += "--continue-on-fail" }

if ($ReleasePolicyRunSecondary) { $argsList += "--release-policy-run-secondary" }
if ($ReleasePolicySecondaryProfile) { $argsList += @("--release-policy-secondary-profile", $ReleasePolicySecondaryProfile) }
if ($ReleasePolicyEnforceSecondary) { $argsList += "--release-policy-enforce-secondary" }
if ($ReleasePolicyStrict) { $argsList += "--release-policy-strict" }

Write-Host "=== Release Stability Check Start ===" -ForegroundColor Cyan
Write-Host "rounds: $Rounds, interval: $IntervalSec sec"
Write-Host "workflow: $WorkflowId"

python @argsList
$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
  Write-Host "Release stability check PASS." -ForegroundColor Green
  exit 0
}
if ($exitCode -eq 2) {
  Write-Host "Release stability check BLOCK." -ForegroundColor Red
  exit 2
}
throw "run_release_stability_check.py failed with exit code: $exitCode"
