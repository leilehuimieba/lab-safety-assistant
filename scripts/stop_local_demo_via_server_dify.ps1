$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$RuntimeFile = Join-Path $RepoRoot "artifacts\local-dify-bridge\runtime.json"

if (-not (Test-Path $RuntimeFile)) {
    Write-Host "[INFO] runtime file not found: $RuntimeFile"
    Write-Host "[INFO] Nothing to stop."
    exit 0
}

$runtime = Get-Content $RuntimeFile -Raw | ConvertFrom-Json

foreach ($targetPid in @($runtime.demo_pid, $runtime.tunnel_pid)) {
    if (-not $targetPid) {
        continue
    }
    try {
        $proc = Get-Process -Id $targetPid -ErrorAction SilentlyContinue
        if ($proc) {
            Stop-Process -Id $targetPid -Force -ErrorAction Stop
            Write-Host "[OK] Stopped PID=$targetPid ($($proc.ProcessName))"
        }
    } catch {
        Write-Host "[WARN] Failed to stop PID=$targetPid : $($_.Exception.Message)"
    }
}

Remove-Item $RuntimeFile -Force -ErrorAction SilentlyContinue
Write-Host "[OK] Local Dify bridge runtime cleaned."
