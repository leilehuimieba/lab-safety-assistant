param(
  [string]$RepoRoot = ".",
  [string]$ReleaseDir = "release_exports/v8.1",
  [string]$WebHealthUrl = "http://127.0.0.1:8088/health",
  [switch]$SkipWebHealth,
  [switch]$AllowWarningPass,
  [switch]$NoEnforceProdPolicy
)

$ErrorActionPreference = "Stop"

$argsList = @(
  "scripts/release/go_live_preflight.py",
  "--repo-root", $RepoRoot,
  "--release-dir", $ReleaseDir,
  "--web-health-url", $WebHealthUrl
)

if ($SkipWebHealth) { $argsList += "--skip-web-health" }
if ($AllowWarningPass) { $argsList += "--allow-warning-pass" }
if ($NoEnforceProdPolicy) { $argsList += "--no-enforce-prod-policy" }

Write-Host "=== Go-Live Preflight Start ===" -ForegroundColor Cyan
Write-Host "repo-root: $RepoRoot"
Write-Host "release-dir: $ReleaseDir"
Write-Host "web-health-url: $WebHealthUrl"

python @argsList
$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
  Write-Host "Go-live preflight PASS." -ForegroundColor Green
  exit 0
}

if ($exitCode -eq 2) {
  Write-Host "Go-live preflight BLOCK." -ForegroundColor Red
  exit 2
}

if ($exitCode -eq 3) {
  Write-Host "Go-live preflight WARN." -ForegroundColor Yellow
  exit 3
}

throw "go_live_preflight.py failed with unexpected exit code: $exitCode"
