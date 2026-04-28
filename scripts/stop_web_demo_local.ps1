$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$RuntimeFile = Join-Path $RepoRoot "artifacts\local-web-demo\runtime.json"

if (-not (Test-Path $RuntimeFile)) {
    Write-Host "[INFO] runtime file not found: $RuntimeFile"
    Write-Host "[INFO] Nothing to stop."
    exit 0
}

$runtime = Get-Content $RuntimeFile -Raw | ConvertFrom-Json
if ($runtime.pid) {
    $proc = Get-Process -Id $runtime.pid -ErrorAction SilentlyContinue
    if ($proc) {
        Stop-Process -Id $runtime.pid -Force -ErrorAction Stop
        Write-Host "[OK] Stopped PID=$($runtime.pid) ($($proc.ProcessName))"
    } else {
        Write-Host "[INFO] PID=$($runtime.pid) is not running."
    }
}

Remove-Item $RuntimeFile -Force -ErrorAction SilentlyContinue
Write-Host "[OK] Local web_demo runtime cleaned."
