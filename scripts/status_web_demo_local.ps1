$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$RepoRoot = Split-Path -Parent $PSScriptRoot
$RuntimeFile = Join-Path $RepoRoot "artifacts\local-web-demo\runtime.json"

if (-not (Test-Path $RuntimeFile)) {
    Write-Host "[INFO] runtime file not found: $RuntimeFile"
    exit 0
}

$runtime = Get-Content $RuntimeFile -Raw | ConvertFrom-Json
$proc = $null
if ($runtime.pid) {
    $proc = Get-Process -Id $runtime.pid -ErrorAction SilentlyContinue
}

Write-Host "started_at : $($runtime.started_at)"
Write-Host "demo_port  : $($runtime.demo_port)"
Write-Host "pid        : $($runtime.pid)"
Write-Host "running    : $([bool]$proc)"
Write-Host "app_version: $($runtime.app_version)"
Write-Host "acceptance : $($runtime.acceptance_status)"
Write-Host "model      : $($runtime.runtime_model)"
Write-Host "lab_mode   : $($runtime.lab_lane_state)"
Write-Host "agent_lane : $($runtime.chat_lane_agent)"
Write-Host "chat_lane  : $($runtime.chat_lane_lab)"
Write-Host "launch_file: $($runtime.launch_file)"
Write-Host "log_file   : $($runtime.log_file)"
Write-Host "err_file   : $($runtime.err_file)"
Write-Host "env_file   : $($runtime.env_file)"
if ($runtime.demo_port) {
    try {
        $health = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$($runtime.demo_port)/health" -TimeoutSec 5
        Write-Host "health     : $($health.StatusCode) $($health.Content)"
    } catch {
        Write-Host "health     : unavailable ($($_.Exception.Message))"
    }
}
